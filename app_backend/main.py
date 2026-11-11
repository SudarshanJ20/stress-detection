"""Loopback-only local analysis service. No sensitive request or measurement logging."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from uuid import UUID

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict
from stress_detection.validate_sample import require_ignored

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('STILL_RUNTIME', ROOT / 'data/processed/still-local'))
CONTRACT = json.loads((ROOT / 'web/lib/gad7.json').read_text())
ORIGINS = {'http://127.0.0.1:3000', 'http://localhost:3000'}
LIMIT = 100 * 1024 * 1024
TTL = 1800

def score(answers):
    if not isinstance(answers, list) or len(answers) != 7 or any(type(x) is not int or not 0 <= x <= 3 for x in answers):
        raise ValueError('Complete all seven items with valid responses.')
    total = sum(answers)
    return {'score': total, 'category': next(b['label'] for b in CONTRACT['bands'] if b['min'] <= total <= b['max']),
            'source': 'GAD-7 questionnaire', 'timeframe': CONTRACT['timeframe'], 'version': CONTRACT['version']}

class NewJob(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str
    provenance: str = 'webcam'
    keep_recording: bool = False

class Store:
    def __init__(self):
        require_ignored(RUNTIME); RUNTIME.mkdir(parents=True, exist_ok=True); RUNTIME.chmod(0o700)
        marker = RUNTIME / '.still-owned'
        if RUNTIME.is_symlink() or (not marker.exists() and any(RUNTIME.iterdir())):
            raise RuntimeError('Use an empty, private Still runtime directory.')
        marker.write_text('still-local-runtime-v1\n')
        self.jobs = {}; self.lock = threading.RLock(); self.pool = ThreadPoolExecutor(max_workers=1)
        (RUNTIME / 'recordings').mkdir(exist_ok=True)
        shutil.rmtree(RUNTIME / 'jobs', ignore_errors=True); (RUNTIME / 'jobs').mkdir()
    def create(self, data):
        try: key = str(UUID(data.request_id))
        except ValueError: raise HTTPException(422, 'Invalid request identifier.')
        if data.provenance not in ('webcam', 'prerecorded'): raise HTTPException(422, 'Invalid recording source.')
        with self.lock:
            if key in self.jobs: return self.jobs[key]
            if sum(j['stage'] not in ('completed', 'failed', 'cancelled') for j in self.jobs.values()) >= 3:
                raise HTTPException(429, 'Analysis queue is full. Wait or cancel a session.')
            folder = RUNTIME / 'jobs' / key; folder.mkdir()
            j = {'id': key, 'stage': 'awaiting_upload', 'source': data.provenance, 'keep': data.keep_recording,
                 'created': time.time(), 'folder': folder, 'process': None, 'deleted': False, 'result': None}
            self.jobs[key] = j; return j
    def get(self, key):
        with self.lock:
            if key not in self.jobs: raise HTTPException(404, 'Session expired or deleted.')
            return self.jobs[key]
    def run(self, j):
        try:
            with self.lock:
                if j['deleted']: return
                j['stage'] = 'checking_video'
                j['process'] = subprocess.Popen([sys.executable, '-m', 'app_backend.worker', str(j['folder']), j['source']],
                    cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            code = j['process'].wait()
            with self.lock:
                if j['deleted']: return
                result = j['folder'] / 'result.json'
                if code == 0 and result.is_file():
                    j['result'] = json.loads(result.read_text()); j['stage'] = 'completed'
                    if j['keep']:
                        shutil.move(j['folder'] / 'input.webm', RUNTIME / 'recordings' / (j['id'] + '.webm'))
                else: j['stage'] = 'failed'
        except Exception:
            with self.lock:
                if not j['deleted']: j['stage'] = 'failed'
        finally:
            shutil.rmtree(j['folder'], ignore_errors=True)
    def delete(self, key):
        with self.lock:
            j = self.jobs.pop(key, None)
            if j: j['deleted'] = True; j['stage'] = 'cancelled'
            process = j['process'] if j else None
        if process and process.poll() is None:
            try: os.killpg(process.pid, signal.SIGTERM); process.wait(timeout=2)
            except ProcessLookupError: pass
            except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
        if j: shutil.rmtree(j['folder'], ignore_errors=True)
        # Only canonical IDs may address recordings, including files retained across restarts.
        try: canonical = str(UUID(key))
        except ValueError: raise HTTPException(422, 'Invalid session identifier.')
        (RUNTIME / 'recordings' / (canonical + '.webm')).unlink(missing_ok=True)
    def clear(self):
        for key in list(self.jobs): self.delete(key)
        for f in (RUNTIME / 'recordings').glob('*.webm'): f.unlink()

store = None

@asynccontextmanager
async def lifespan(app):
    global store
    store = Store()
    async def sweep():
        while True:
            await asyncio.sleep(60)
            for key, job in list(store.jobs.items()):
                if time.time() - job['created'] > TTL:
                    if job['keep'] and job['stage'] == 'completed': store.jobs.pop(key, None)
                    else: await asyncio.to_thread(store.delete, key)
    sweeper = asyncio.create_task(sweep())
    yield
    sweeper.cancel()
    for key in list(store.jobs):
        # Cancel ephemeral jobs; explicitly retained recordings survive server restart.
        j = store.jobs[key]; keep = j['keep'] and j['stage'] == 'completed'
        if keep: store.jobs.pop(key)
        else: await asyncio.to_thread(store.delete, key)
    store.pool.shutdown(wait=True, cancel_futures=True)

app = FastAPI(title='Still local observations', docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

@app.middleware('http')
async def local_only(request, call_next):
    if request.method not in ('GET', 'HEAD') and (request.headers.get('x-still-local') != '1' or request.headers.get('origin') not in ORIGINS):
        return JSONResponse({'detail': 'Use the local Still application.'}, status_code=403)
    response = await call_next(request); response.headers['Cache-Control'] = 'no-store'; return response

@app.exception_handler(RequestValidationError)
async def invalid(request, exc): return JSONResponse({'detail': 'Invalid request. Check required fields.'}, status_code=422)

@app.get('/api/health')
def health():
    return {'status': 'ready', 'version': '1.0.0', 'model_available': (ROOT / 'models/mediapipe/face_landmarker.task').is_file(),
            'retention_minutes': 30, 'capture_target_seconds': 35, 'minimum_window_seconds': 30}

@app.post('/api/score')
async def scoring(request: Request):
    try: return score((await request.json()).get('answers'))
    except (ValueError, AttributeError): raise HTTPException(422, 'Complete all seven items with valid responses.')

@app.post('/api/jobs')
def create(data: NewJob):
    if not (ROOT / 'models/mediapipe/face_landmarker.task').is_file(): raise HTTPException(503, 'Local landmark model is unavailable.')
    j = store.create(data); return {'id': j['id'], 'stage': j['stage']}

@app.put('/api/jobs/{key}/video')
async def upload(key: str, request: Request):
    j = store.get(key)
    if request.headers.get('content-type', '').split(';')[0] not in ('video/webm', 'video/mp4', 'video/quicktime'):
        raise HTTPException(415, 'Choose a supported video recording.')
    with store.lock:
        if j['stage'] != 'awaiting_upload': raise HTTPException(409, 'This recording was already submitted.')
        j['stage'] = 'receiving_video'
    try:
        n = 0
        with (j['folder'] / 'input.webm').open('xb') as target:
            async for chunk in request.stream():
                n += len(chunk)
                if n > LIMIT: raise HTTPException(413, 'Recording exceeds the 100 MiB local limit.')
                if j['deleted']: raise HTTPException(409, 'Recording was cancelled.')
                target.write(chunk)
        if n == 0: raise HTTPException(422, 'Recording is empty.')
        with store.lock:
            if j['deleted']: raise HTTPException(409, 'Recording was cancelled.')
            j['stage'] = 'queued'; store.pool.submit(store.run, j)
        return {'id': key, 'stage': 'queued'}
    except BaseException:
        j['stage'] = 'failed'; shutil.rmtree(j['folder'], ignore_errors=True); raise

@app.get('/api/jobs/{key}')
def job(key: str):
    j = store.get(key); stage = j['stage']
    if stage not in ('completed', 'failed') and (j['folder'] / 'stage.json').is_file():
        try:
            stage = json.loads((j['folder'] / 'stage.json').read_text())['stage']
            if stage == 'completed': stage = 'summarizing'
        except (OSError, ValueError): pass
    return {'id': key, 'stage': stage, 'result': j['result'], 'recording_saved': (RUNTIME / 'recordings' / (key + '.webm')).is_file(),
            'message': 'Analysis could not finish. Check recording length, readable video, timing and local model availability.' if stage == 'failed' else None}

@app.delete('/api/jobs/{key}')
def delete(key: str): store.delete(key); return {'deleted': True}

@app.get('/api/recordings')
def recordings(): return {'recordings': [{'id': p.stem, 'created': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()} for p in (RUNTIME / 'recordings').glob('*.webm')]}

@app.delete('/api/jobs')
def clear(): store.clear(); return {'deleted': True}
