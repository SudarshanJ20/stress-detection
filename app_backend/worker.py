"""Isolated observation worker. Never imports or runs an anxiety regressor."""
import json
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
from importlib.metadata import version
from statistics import median
from stress_detection.pilot_state import atomic, read
from stress_detection import pulse, features
from stress_detection.pulse_diagnostics import edge_info
from stress_detection.video_reader import VideoReader

ROOT = Path(__file__).resolve().parents[1]

def summarize(face, pulse_run, provenance):
    config, times, _, timing = pulse.load_face_run(face)
    summary = read(face / 'summary.json'); duration = timing['duration_seconds']
    windows = []; group = []; current = 0; origin = times[0]; previous = None
    def emit():
        b, q = features.summarize_frames(group, summary['reader']['width'], summary['reader']['height'])
        return {'index': current, 'facial': b, 'quality': q}
    with (face / 'frames.jsonl').open() as source:
        for line in source:
            row = json.loads(line); t = row['presentation_time_seconds']; index = int((t - origin) // 30)
            row['_previous_gap'] = t - previous if previous is not None else None; previous = t
            if index != current:
                if (current + 1) * 30 <= duration + 1e-9: windows.append(emit())
                group = []; current = index
            group.append(row)
    if (current + 1) * 30 <= duration + 1e-9: windows.append(emit())
    estimates = read(face / 'summary.json')
    pulse_rows = features.read_jsonl(pulse_run / 'windows.jsonl')
    for row in pulse_rows:
        row['near_band_edge'] = edge_info(row['estimated_bpm'], 2, pulse.Settings())['near_edge_within_one_bin'] if row['status'] == 'accepted' else None
    facial = {}
    for name in features.BEHAVIOUR:
        values = [w['facial'][name] for w in windows if w['facial'][name] is not None]
        facial[name] = {'value': median(values) if values else None, 'supported_windows': len(values), 'scheduled_windows': len(windows)}
    return {'source': provenance, 'duration_seconds': duration, 'window_seconds': 30, 'scheduled_windows': len(windows),
            'facial': facial, 'pulse': pulse_rows, 'windows': windows,
            'quality': {k: estimates.get(k) for k in ('tracked_coverage', 'region_coverage', 'missing_face_frames', 'multiple_face_frames', 'processed_frames', 'track_event_counts')},
            'versions': {'app': '1.0.0', 'policy': 'pilot-camera-v1', 'feature_schema': 'window-features-v1',
                         'model_sha256': config['model']['sha256'], 'policy_stamp': config.get('policy'), 'python': sys.version.split()[0],
                         **{k: version(k) for k in ('av', 'mediapipe', 'numpy')}, 'pulse_settings': asdict(pulse.Settings())},
            'interpretation': 'Screened camera pulse and geometric proxies; no anxiety model or calibrated confidence. Camera timing is container-reported, not independently validated.',
            'availability': 'complete_intervals' if windows else 'insufficient_recording_length'}

def main():
    folder = Path(sys.argv[1]); provenance = sys.argv[2]; source = folder / 'input.webm'
    def stage(value): atomic(folder / 'stage.json', {'stage': value})
    try:
        stage('checking_video')
        with VideoReader(source) as reader:
            for i, frame in enumerate(reader):
                if i > 10000 or (frame.relative_time is not None and frame.relative_time > 240):
                    raise ValueError('recording_limit')
        stage('extracting_face')
        subprocess.run([sys.executable, '-m', 'stress_detection.face_quality', '--input', str(source), '--output', str(folder / 'face'),
                        '--model', str(ROOT / 'models/mediapipe/face_landmarker.task'), '--model-config', str(ROOT / 'configs/face-landmarker.json'),
                        '--policy', str(ROOT / 'configs/pilot-policy-v1.json')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        stage('screening_pulse')
        subprocess.run([sys.executable, '-m', 'stress_detection.pulse', '--face-run', str(folder / 'face'), '--output', str(folder / 'pulse')],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        stage('summarizing')
        atomic(folder / 'result.json', summarize(folder / 'face', folder / 'pulse', provenance)); stage('completed')
    except Exception:
        stage('failed')
        sys.exit(1)

if __name__ == '__main__': main()
