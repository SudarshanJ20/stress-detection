"""Synthetic diagnostics and actual browser VP8 → decoder RGB round-trip."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
from app_backend.video_diagnostics import band_component, candidate_band, clean, correlation, checked_signal
from stress_detection.pulse import Settings
from stress_detection.video_reader import VideoReader

ROOT = Path(__file__).resolve().parents[1]

class VideoDiagnosticsTests(unittest.TestCase):
    def test_nulls_and_constant_correlations_are_not_measurements(self):
        self.assertEqual(json.loads(json.dumps(clean({'values': np.array([np.nan, np.inf, 2]), 'flag': np.bool_(False)}), allow_nan=False)), {'values': [None, None, 2.0], 'flag': False})
        self.assertIsNone(correlation(np.ones(10), np.arange(10)))
        self.assertIsNone(candidate_band(np.arange(3), np.zeros(3), 60))

    def test_band_inspection_excludes_drift_without_changing_input_or_settings(self):
        cfg = Settings(); t = np.arange(1200)/40
        signal = np.sin(2*np.pi*2.5*t) + 10*np.sin(2*np.pi*.1*t)
        original = signal.copy()
        band = band_component(signal, 40, cfg)
        np.testing.assert_array_equal(signal, original)
        self.assertAlmostEqual(correlation(band, np.sin(2*np.pi*2.5*t)), 1)
        self.assertEqual(cfg.min_peak_fraction, .1)

    def test_flat_diagnostic_has_no_invented_peak_and_replay_mismatch_fails(self):
        cfg = Settings()
        row = {'status': 'rejected', 'rejection_reason': 'flat_signal', 'estimated_bpm': None, 'spectral_peak_fraction': None}
        diagnostic, _ = checked_signal(np.ones(1200), row, cfg)
        self.assertIsNone(diagnostic['winning_bin'])
        self.assertIsNone(diagnostic['estimated_bpm'])
        self.assertEqual(diagnostic['strongest_in_band_bins'], [])
        with self.assertRaisesRegex(ValueError, 'differs from production'):
            checked_signal(np.ones(1200), {**row, 'estimated_bpm': 42}, cfg)

    def test_browser_vp8_channels_dimensions_timing_and_private_fixture_cleanup(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data/processed') as folder:
            path = Path(folder)/'colors.webm'
            subprocess.run(['node', 'tests/helpers/record-colors.cjs', str(path)], cwd=ROOT/'web', check=True, capture_output=True, timeout=30)
            count = 0
            with VideoReader(path) as reader:
                for frame in reader:
                    rgb = frame.rgb.to_ndarray(format='rgb24')
                    self.assertEqual(rgb.shape, (240, 480, 3))
                    for x, target in [(80,[255,0,0]), (240,[0,255,0]), (400,[0,0,255])]:
                        np.testing.assert_allclose(rgb[50:190,x-20:x+20].mean(axis=(0,1)), target, atol=10)
                    count += 1
                summary = reader.summary()
            self.assertGreater(count, 20)
            self.assertGreater(summary['pts_span_seconds'], .9)
            # Chromium may omit final-frame extent. Do not invent duration from FPS.
            if summary['last_frame_duration_seconds'] is None:
                self.assertIsNone(summary['observed_duration_seconds'])
            self.assertEqual(summary['nonmonotonic_pts'], 0)
            self.assertEqual(summary['missing_pts'], 0)
        self.assertFalse(path.exists())


class PrivateBundleTests(unittest.TestCase):
    def test_no_opt_in_creates_nothing(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data/processed') as folder:
            output = Path(folder)/'absent'
            result = subprocess.run([str(ROOT/'.venv/bin/python'), '-m', 'app_backend.video_diagnostics', '--recording', '/not/read', '--output', str(output)], cwd=ROOT, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_failed_replay_removes_owned_copy_and_preserves_original(self):
        from unittest.mock import patch
        from app_backend.video_diagnostics import collect, delete_bundle, OWNERSHIP
        with tempfile.TemporaryDirectory(dir=ROOT/'data/processed') as folder:
            folder = Path(folder); original = folder/'source.webm'; original.write_bytes(b'original video')
            output = folder/'bundle'
            with patch('app_backend.video_diagnostics.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'worker')):
                with self.assertRaises(subprocess.CalledProcessError): collect(original, output)
            self.assertFalse(output.exists()); self.assertEqual(original.read_bytes(), b'original video')
            output.mkdir(); (output/'unowned.txt').write_text('preserve')
            with self.assertRaises(ValueError): delete_bundle(output)
            self.assertTrue((output/'unowned.txt').exists())
            (output/'.still-diagnostic-owned').write_text(OWNERSHIP)
            delete_bundle(output)
            self.assertFalse(output.exists()); self.assertTrue(original.exists())

if __name__ == '__main__': unittest.main()
