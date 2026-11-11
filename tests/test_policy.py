"""Frozen policy registration, runtime enforcement and receipt invalidation."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from stress_detection.policy import DEFAULT_POLICY, load_policy
from stress_detection.pilot import context
from stress_detection.pilot_state import StageStore, atomic, digest, read

ROOT = Path(__file__).resolve().parents[1]


class PolicyTests(unittest.TestCase):
    def test_registered_config_and_runtime_defaults_are_frozen(self):
        policy, stamp = load_policy()
        self.assertTrue(policy['tracking']['measurements']['reacquire_enabled'])
        self.assertEqual(policy['pulse']['settings']['max_gap_seconds'], .15)
        self.assertEqual(stamp['timing'], 'decoded-pts-v1')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'policy.json'
            for changed in ('version', 'threshold'):
                bad = copy.deepcopy(policy)
                if changed == 'version':
                    bad['version'] = 'unknown'
                else:
                    bad['tracking']['measurements']['reacquire_min_frames'] = 1
                path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError, 'Unknown or modified'):
                    load_policy(path)
        with patch('stress_detection.face_quality.DEFAULT_CONFIG', {}):
            with self.assertRaisesRegex(ValueError, 'Implementation defaults'):
                load_policy()
        with self.assertRaisesRegex(ValueError, 'Track override'):
            context(Path('unused'), Path('unused'), 'contiguous')

    def test_policy_stamp_is_required_for_resume_and_version_changes_invalidate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'data/processed') as tmp:
            root = Path(tmp)
            store = StageStore(root)
            specification = {'context': {'policy': load_policy()[1]}}
            def action(output, log):
                output.mkdir()
                atomic(output / 'status.json', {'status': 'completed'})
            first = store.run('synthetic', specification, action, Mock())
            self.assertEqual(first['policy'], specification['context']['policy'])
            self.assertIsNotNone(store.lookup('synthetic', digest(specification)))
            receipt = Path(first['receipt'])
            meta = read(receipt)
            meta.pop('policy')
            atomic(receipt, meta)
            self.assertIsNone(store.lookup('synthetic', digest(specification)))
            meta['policy'] = specification['context']['policy']
            atomic(receipt, meta)
            other = copy.deepcopy(specification)
            other['context']['policy']['version'] = 'future'
            self.assertIsNone(store.lookup('synthetic', digest(other)))

    def test_reference_only_import_does_not_require_compatible_camera_output(self):
        import numpy as np
        from stress_detection.pilot import save_reference, verify_reference
        with tempfile.TemporaryDirectory(dir=ROOT / 'data/processed') as tmp:
            root = Path(tmp)
            signal = root / 'synthetic.csv'
            np.savetxt(signal, np.sin(2 * np.pi * 1.2 * np.arange(1920) / 64))
            old = root / 'old-pulse'
            save_reference(old, signal)
            atomic(old / 'config.json', {'old_camera_settings': True})
            action = Mock()
            result = StageStore(root / 'stages').run(
                'reference', {'context': {'policy': load_policy()[1]}}, action,
                lambda path: verify_reference(path, signal), old)
            action.assert_not_called()
            self.assertEqual(result['decision'], 'import')
            self.assertEqual(read(old / 'config.json'), {'old_camera_settings': True})
            signal.write_text('0\n' * 1920)
            with self.assertRaises(ValueError):
                verify_reference(old, signal)

    def test_face_command_rejects_conflicting_policy_before_processing(self):
        from stress_detection.face_quality import run_video
        with self.assertRaisesRegex(ValueError, 'Face settings conflict'):
            run_video('unused', 'unused', 'unused', {}, policy_path=DEFAULT_POLICY,
                      measurement_config={'reacquire_enabled': False})

    def test_legacy_face_without_policy_stamp_requires_explicit_refresh(self):
        from stress_detection.pilot import verify_face
        policy, stamp = load_policy()
        software = {p: 'synthetic' for p in ('av', 'mediapipe', 'numpy', 'opencv-contrib-python')}
        ctx = {'policy': stamp, 'face_settings': policy['tracking']['measurements'],
               'model': {}, 'python': 'synthetic', 'software': software}
        record = {'files': {'vid': {'sha256': 'synthetic'}}, 'recording_id': 's999/T1',
                  'video': {'decoded_frames': 1}}
        cfg = {'max_frames': None, 'source': record['files']['vid'],
               'recording_id': record['recording_id'], 'model': {}, 'python': 'synthetic',
               'software': software, 'measurements': ctx['face_settings']}
        with patch('stress_detection.pilot.load_face_run', return_value=(cfg, [0], {}, {})), \
                patch('stress_detection.pilot.read', return_value={'reader': {'decoded_frames': 1}}):
            with self.assertRaisesRegex(ValueError, 'provenance/settings'):
                verify_face(Path('unused'), record, ctx)
            cfg['policy'] = stamp
            verify_face(Path('unused'), record, ctx)
