"""Synthetic validation fixtures only; never load participant data."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from stress_detection.validate_sample import inspect_info, inspect_numeric, main, missing_files, video_integrity


class SignalValidationTests(unittest.TestCase):
    def inspect(self, text, columns=1, rate=4):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.csv"
            path.write_text(text)
            return inspect_numeric(path, columns, rate)

    def test_valid_signal_duration(self):
        result = self.inspect("1\n2\n3\n4\n")
        self.assertTrue(result["valid"])
        self.assertEqual(result["rows"], 4)
        self.assertEqual(result["nominal_duration_seconds"], 1)

    def test_malformed_values_are_not_silently_dropped(self):
        result = self.inspect("1\n\n\"\"\nhello\nnan\ninf\n2,3\n")
        self.assertFalse(result["valid"])
        self.assertEqual(result["rows"], 7)
        self.assertEqual(result["missing"], 2)
        self.assertEqual(result["nonnumeric"], 1)
        self.assertEqual(result["nonfinite"], 2)
        self.assertEqual(result["malformed_rows"], [2, 7])
        self.assertIsNone(result["nominal_duration_seconds"])

    def test_header_and_empty_file_rejected(self):
        self.assertFalse(self.inspect("value\n1\n")["valid"])
        self.assertFalse(self.inspect("")["valid"])

    def test_broken_quoting_rejected(self):
        self.assertFalse(self.inspect('"unterminated\n')["valid"])

    def test_questionnaire_column_shape(self):
        self.assertTrue(self.inspect("1,2\n3,4\n2,3\n", columns=2)["valid"])
        self.assertFalse(self.inspect("1,2\n3\n2,3\n", columns=2)["valid"])


class PairValidationTests(unittest.TestCase):
    def test_decoded_integrity_separates_count_metadata_and_timestamp_failure(self):
        good = {'decoded_frames': 100, 'declared_frames': 101, 'decode_complete': True,
                'last_frame_duration_seconds': .04, 'observed_duration_seconds': 4.04,
                'gap_intervals': 1, 'irregular_intervals': 1}
        result = video_integrity(good)
        self.assertTrue(result['valid'])
        self.assertFalse(result['metadata_frame_count_matches'])
        for key, value in [('missing_pts', 1), ('missing_time_base', 1), ('duplicate_pts', 1),
                           ('nonmonotonic_pts', 1), ('corrupt_frames', 1), ('decoder_error_count', 1),
                           ('decode_complete', False), ('last_frame_duration_seconds', None)]:
            with self.subTest(key=key):
                self.assertFalse(video_integrity({**good, key: value})['valid'])

    def test_duration_comparison_uses_observed_pts_extent_with_gaps(self):
        root = Path(__file__).resolve().parents[1] / 'data/processed'
        with tempfile.TemporaryDirectory(dir=root) as directory:
            folder = Path(directory) / 's999'
            folder.mkdir()
            for task in (1, 2, 3):
                (folder / f'vid_s999_T{task}.avi').touch()
                (folder / f'bvp_s999_T{task}.csv').write_text('1\n' * 64)
                (folder / f'eda_s999_T{task}.csv').write_text('1\n' * 4)
            (folder / 'info_s999.txt').write_text('999\nf\nctrl\n2000-01-01\n12-00-00\n')
            (folder / 'selfReportedAnx_s999.csv').write_text('1,1\n1,1\n1,1\n')
            output = Path(directory) / 'validation'
            video = {'valid': True, 'frame_rate': 25, 'observed_duration_seconds': 1.08,
                     'decoded_duration_at_nominal_rate_seconds': 1.0}
            with patch('sys.argv', ['validator', str(folder), '--output', str(output)]), \
                    patch('stress_detection.validate_sample.inspect_video', side_effect=lambda *args: dict(video)):
                main()
            report = json.loads((output / 'validation.json').read_text())
            self.assertTrue(all(v['duration_discrepancy'] for v in report['videos']))
            self.assertAlmostEqual(report['videos'][0]['signal_duration_deltas_seconds']['bvp'], .08)

    def test_missing_reference_and_video_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "s999"
            folder.mkdir()
            for task in (1, 2, 3):
                for kind, suffix in (("vid", "avi"), ("bvp", "csv"), ("eda", "csv")):
                    (folder / f"{kind}_s999_T{task}.{suffix}").touch()
            (folder / "info_s999.txt").touch()
            (folder / "selfReportedAnx_s999.csv").touch()
            self.assertEqual(missing_files(folder), [])
            (folder / "bvp_s999_T2.csv").unlink()
            (folder / "vid_s999_T3.avi").unlink()
            self.assertEqual(set(missing_files(folder)), {"bvp_s999_T2.csv", "vid_s999_T3.avi"})

    def test_metadata_format_variation_and_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "info_s999.txt"
            path.write_text("999\nf\nctrl\n2000_01_01\n12_00_00\n")
            result = inspect_info(path, "s999")
            self.assertTrue(result["valid"])
            self.assertFalse(result["documentation_date_format_matches"])
            self.assertNotIn("2000_01_01", str(result))
            self.assertFalse(inspect_info(path, "s998")["valid"])


if __name__ == "__main__":
    unittest.main()
