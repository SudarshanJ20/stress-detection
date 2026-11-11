"""Registered engineering policies; edits require a new version and review."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

DEFAULT_POLICY = Path(__file__).resolve().parents[2] / 'configs/pilot-policy-v1.json'
REGISTERED = {'pilot-camera-v1': 'c399e9c4c10caf9021c8132044fdff08a53589580d5e2512e83c2dd663852875'}


def load_policy(path=DEFAULT_POLICY):
    policy = json.loads(Path(path).read_text())
    checksum = hashlib.sha256(json.dumps(policy, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if REGISTERED.get(policy.get('version')) != checksum:
        raise ValueError('Unknown or modified frozen policy; register a new reviewed version')
    from .face_quality import DEFAULT_CONFIG
    from .pulse import Settings
    from .validate_sample import video_integrity
    if (policy['timing']['version'] != video_integrity({})['camera_eligibility_policy']
            or policy['tracking']['measurements'] != {**DEFAULT_CONFIG, 'reacquire_enabled': True}
            or policy['pulse']['settings'] != asdict(Settings())):
        raise ValueError('Implementation defaults differ from frozen policy')
    stamp = {'version': policy['version'], 'sha256': checksum,
             'timing': policy['timing']['version'], 'tracking': policy['tracking']['version'],
             'pulse': policy['pulse']['version']}
    return policy, stamp
