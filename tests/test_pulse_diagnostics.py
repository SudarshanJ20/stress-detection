"""Synthetic diagnostics: no participant traces or values."""

from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

import numpy as np

from stress_detection.pulse import Settings, spectral_rate
from stress_detection.pulse_diagnostics import describe_signal, edge_info, longest_run, plot_windows


class DiagnosticsTests(unittest.TestCase):
    def test_no_complete_reference_windows_still_produces_diagnostic_plot(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'data/processed') as folder:
            output = Path(folder) / 'empty.png'
            plot_windows([], output, 64, Settings())
            self.assertTrue(output.read_bytes().startswith(b'\x89PNG'))

    def test_rate_axis_bpm_and_detrend_with_drift(self):
        t = np.arange(1920) / 64
        x = np.sin(2 * np.pi * 1.5 * t) + .4 * t + 20
        report, (_, frequencies, _) = describe_signal(x, 64, Settings())
        self.assertEqual(report['estimated_bpm'], 90)
        self.assertEqual(report['bin_spacing_bpm'], 2)
        self.assertEqual(frequencies[-1], 32)
        self.assertEqual(report['winning_bin']['hz'], 1.5)
        self.assertAlmostEqual(report['linear_slope_units_per_second'], .4, delta=.002)
        self.assertEqual(report['status'], 'accepted')

    def test_diffuse_decision_matches_production_without_tuning(self):
        cfg = Settings()
        original = asdict(cfg)
        x = np.random.default_rng(84).normal(size=1920)
        report, _ = describe_signal(x, 64, cfg)
        bpm, fraction, reason = spectral_rate(x, 64, cfg)
        self.assertIsNone(bpm)
        self.assertEqual(reason, 'diffuse_spectrum')
        self.assertEqual(report['spectral_peak_fraction'], fraction)
        self.assertLess(report['threshold_margin'], 0)
        self.assertEqual(asdict(cfg), original)

    def test_flat_and_repeated_extrema_are_observations(self):
        report, _ = describe_signal(np.ones(1920), 64, Settings())
        self.assertEqual(report['rejection_reason'], 'flat_signal')
        self.assertEqual(report['longest_exact_constant_samples'], 1920)
        self.assertEqual(report['longest_maximum_run_samples'], 1920)
        self.assertEqual(longest_run([False, True, True, False, True]), 2)

    def test_edge_annotation_is_not_acceptance_threshold(self):
        for bpm in (42, 44, 238, 240):
            self.assertTrue(edge_info(bpm, 2, Settings())['near_edge_within_one_bin'])
        self.assertFalse(edge_info(46, 2, Settings())['near_edge_within_one_bin'])
        self.assertFalse(edge_info(10, 2, Settings())['near_edge_within_one_bin'])
        self.assertIsNone(edge_info(None, 2, Settings()))


if __name__ == '__main__':
    unittest.main()
