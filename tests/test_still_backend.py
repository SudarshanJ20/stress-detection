"""Local app boundaries: scoring, privacy guards, jobs, cancellation and deletion."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from app_backend import main

ROOT=Path(__file__).resolve().parents[1]
HEADERS={'origin':'http://127.0.0.1:3000','x-still-local':'1'}
class StillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'data/processed');self.addCleanup(self.tmp.cleanup)
        self.runtime=Path(self.tmp.name)/'runtime';p=patch.object(main,'RUNTIME',self.runtime);p.start();self.addCleanup(p.stop)
        self.client=TestClient(main.app);self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
    def create(self):
        key=str(uuid4());r=self.client.post('/api/jobs',headers=HEADERS,json={'request_id':key,'provenance':'prerecorded'})
        self.assertEqual(r.status_code,200);return key
    def test_all_scoring_totals_boundaries_and_incomplete_inputs(self):
        for total in range(22):
            remaining=total;answers=[]
            for _ in range(7):answers.append(min(3,remaining));remaining=max(0,remaining-3)
            expected='Minimal' if total<5 else 'Mild' if total<10 else 'Moderate' if total<15 else 'Severe'
            self.assertEqual(main.score(answers)['score'],total);self.assertEqual(main.score(answers)['category'],expected)
            r=self.client.post('/api/score',headers=HEADERS,json={'answers':answers});self.assertEqual(r.json(),main.score(answers))
        for answers in [[],[0]*6,[0]*8,[0,0,0,0,0,0,None],[True]*7,[1.5]*7,['1']*7,[4]*7,[-1]*7]:
            r=self.client.post('/api/score',headers=HEADERS,json={'answers':answers});self.assertEqual(r.status_code,422)
            self.assertEqual(r.json()['detail'],'Complete all seven items with valid responses.')
    def test_origin_and_request_validation_do_not_echo_sensitive_data(self):
        self.assertEqual(self.client.post('/api/score',json={'answers':[0]*7}).status_code,403)
        self.assertEqual(self.client.post('/api/score',headers={**HEADERS,'origin':'https://elsewhere.example'},json={'answers':[0]*7}).status_code,403)
        r=self.client.post('/api/jobs',headers=HEADERS,json={'request_id':str(uuid4()),'private_note':'PRIVATE RESPONSE'})
        self.assertEqual(r.status_code,422);self.assertNotIn('PRIVATE RESPONSE',r.text)
    def test_duplicate_job_upload_limit_empty_video_and_delete(self):
        key=self.create();self.assertEqual(self.client.post('/api/jobs',headers=HEADERS,json={'request_id':key}).json()['id'],key)
        self.assertEqual(len(main.store.jobs),1)
        with patch.object(main,'LIMIT',3):
            r=self.client.put(f'/api/jobs/{key}/video',headers={**HEADERS,'content-type':'video/webm'},content=b'1234')
        self.assertEqual(r.status_code,413);self.assertFalse((self.runtime/'jobs'/key).exists())
        self.assertEqual(self.client.delete('/api/jobs/'+key,headers=HEADERS).status_code,200)
        self.assertEqual(self.client.get('/api/jobs/'+key).status_code,404)
        key=self.create();r=self.client.put('/api/jobs/'+key+'/video',headers={**HEADERS,'content-type':'video/webm'},content=b'')
        self.assertEqual(r.status_code,422)
    def test_jobs_run_outside_requests_and_duplicate_upload_is_rejected(self):
        key=self.create()
        with patch.object(main.store.pool,'submit') as submit:
            r=self.client.put('/api/jobs/'+key+'/video',headers={**HEADERS,'content-type':'video/webm'},content=b'video bytes')
            self.assertEqual(r.status_code,200);submit.assert_called_once()
            self.assertEqual(self.client.get('/api/jobs/'+key).json()['stage'],'queued')
            self.assertEqual(self.client.put('/api/jobs/'+key+'/video',headers={**HEADERS,'content-type':'video/webm'},content=b'video').status_code,409)
    def test_cancellation_terminates_process_group_and_removes_owned_files(self):
        key=self.create();process=Mock(pid=12345);process.poll.return_value=None;main.store.jobs[key]['process']=process
        saved=self.runtime/'recordings'/(key+'.webm');saved.write_bytes(b'private recording')
        with patch.object(main.os,'killpg') as kill:
            self.client.delete('/api/jobs/'+key,headers=HEADERS);kill.assert_called_once()
        self.assertFalse(saved.exists());self.assertFalse((self.runtime/'jobs'/key).exists())
        self.assertEqual(self.client.delete('/api/jobs/not-a-uuid',headers=HEADERS).status_code,422)
    def test_clear_deletes_retained_recordings_even_without_job_metadata(self):
        saved=self.runtime/'recordings'/(str(uuid4())+'.webm');saved.write_bytes(b'private')
        self.create();self.assertTrue(self.client.delete('/api/jobs',headers=HEADERS).json()['deleted'])
        self.assertFalse(list((self.runtime/'recordings').iterdir()));self.assertFalse(main.store.jobs)

    def test_worker_launch_failure_becomes_failed_and_cleans_temporary_files(self):
        key=self.create();job=main.store.jobs[key]
        with patch.object(main.subprocess,'Popen',side_effect=OSError('local launch failure')):
            main.store.run(job)
        self.assertEqual(job['stage'],'failed');self.assertFalse(job['folder'].exists())
