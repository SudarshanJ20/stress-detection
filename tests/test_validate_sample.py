"""Synthetic validation fixtures only; never load participant data."""

from pathlib import Path
import tempfile
import unittest

from stress_detection.validate_sample import inspect_info, inspect_numeric, missing_files


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
