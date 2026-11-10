"""Content-verified stage receipts use only synthetic private fixtures."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from stress_detection.pilot_state import StageStore, atomic, digest, inventory, read

ROOT = Path(__file__).resolve().parents[1]


class StageStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'data/processed')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = StageStore(self.root / 'stages')

    def action(self, output, log):
        output.mkdir()
        (output / 'status.json').write_text('{"status":"completed"}')
        (output / 'result.json').write_text('{"value":1}')

    def verify(self, output):
        if read(output / 'status.json')['status'] != 'completed':
            raise ValueError('not completed')

    def test_content_verified_resume_and_changed_input_or_settings(self):
        action = Mock(side_effect=self.action)
        first = self.store.run('s999/face', {'input': 'hash1', 'setting': 1}, action, self.verify)
        second = self.store.run('s999/face', {'input': 'hash1', 'setting': 1}, action, self.verify)
        self.assertEqual(first['decision'], 'run')
        self.assertEqual(second['decision'], 'resume')
        self.assertEqual(action.call_count, 1)
        # Same-length output corruption must invalidate resume.
        (Path(first['output']) / 'result.json').write_text('{"value":2}')
        third = self.store.run('s999/face', {'input': 'hash1', 'setting': 1}, action, self.verify)
        self.assertEqual(third['decision'], 'run')
        self.assertNotEqual(first['output'], third['output'])
        self.store.run('s999/face', {'input': 'hash2', 'setting': 1}, action, self.verify)
        self.store.run('s999/face', {'input': 'hash2', 'setting': 2}, action, self.verify)
        self.assertEqual(action.call_count, 4)
        self.assertTrue(Path(first['output']).exists())

    def test_partial_failed_and_crashed_attempts_never_resume(self):
        def partial(output, log):
            output.mkdir()
            (output / 'status.json').write_text('{"status":"running"}')
        with self.assertRaises(ValueError):
            self.store.run('s999/face', {}, partial, self.verify)
        receipt = next(self.root.rglob('receipt.json'))
        self.assertEqual(read(receipt)['status'], 'failed')
        meta = read(receipt)
        meta['status'] = 'running'
        atomic(receipt, meta)  # abrupt process termination leaves running
        self.assertIsNone(self.store.lookup('s999/face', digest({})))
        result = self.store.run('s999/face', {}, self.action, self.verify)
        self.assertEqual(result['decision'], 'run')
        self.assertEqual(read(receipt)['status'], 'running')

    def test_nonzero_command_cannot_be_promoted_even_with_complete_files(self):
        def failed(output, log):
            self.action(output, log)
            raise RuntimeError('synthetic process failed after writing')
        with self.assertRaises(RuntimeError):
            self.store.run('s999/pulse', {}, failed, self.verify)
        self.assertIsNone(self.store.lookup('s999/pulse', digest({})))

    def test_import_verifies_and_preserves_original(self):
        original = self.root / 'original'
        self.action(original, None)
        before = inventory(original)
        action = Mock()
        result = self.store.run('s999/face', {}, action, self.verify, original)
        self.assertEqual(result['decision'], 'import')
        action.assert_not_called()
        self.assertEqual(before, inventory(original))
        (original / 'status.json').write_text('{"status":"partial"}')
        result = self.store.run('s999/face', {}, self.action, self.verify, original)
        self.assertEqual(result['decision'], 'run')
        self.assertIn('candidate_rejected', result)


if __name__ == '__main__':
    unittest.main()
