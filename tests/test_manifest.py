"""Pairing and manifest tests use only generated, nonparticipant fixtures."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stress_detection.manifest import build_manifest, discover
from stress_detection.validate_splits import validate_splits
from test_video_reader import make_video


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.subject = self.root / "s999"
        self.subject.mkdir()

    def fixture(self):
        for task in (1, 2, 3):
            (self.subject / f"vid_s999_T{task}.avi").write_bytes(b"synthetic video stub")
            (self.subject / f"bvp_s999_T{task}.csv").write_text("1\n" * 64)
            (self.subject / f"eda_s999_T{task}.csv").write_text("1\n" * 4)

    def test_missing_video_and_reference_pairs(self):
        self.fixture()
        (self.subject / "bvp_s999_T1.csv").unlink()
        (self.subject / "vid_s999_T2.avi").unlink()
        records, issues = discover(self.root)
        self.assertEqual(issues, [])
        self.assertIn("missing_bvp", records[0]["warnings"])
        self.assertIn("missing_vid", records[1]["warnings"])
        self.assertEqual([r["task_id"] for r in records], ["T1", "T2", "T3"])

    def test_explicit_participant_scope_never_inspects_unselected_data(self):
        self.fixture()
        other = self.root / 's998'
        other.mkdir()
        (other / 'vid_s998_T1.avi').write_bytes(b'unselected')
        with patch('stress_detection.manifest.inspect_video', return_value={
                'valid': True, 'observed_duration_seconds': 1, 'frame_rate': 25,
                'timing_warnings': []}) as inspect:
            report = build_manifest(self.root, 's999')
        self.assertEqual(inspect.call_count, 3)
        self.assertEqual({r['participant_id'] for r in report['records']}, {'s999'})
        self.assertEqual(report['records'][0]['files']['vid']['path'], 's999/vid_s999_T1.avi')
        for selection in ('../s999', 's997'):
            with self.assertRaises(ValueError):
                discover(self.root, selection)

    def test_ambiguous_backup_is_not_chosen(self):
        self.fixture()
        (self.subject / "bvp_s999_T1 (1).csv").write_text("0\n")
        records, issues = discover(self.root)
        self.assertEqual(len(records[0]["candidates"]["bvp"]), 2)
        self.assertIn("ambiguous_bvp", records[0]["warnings"])
        self.assertEqual(issues[0]["code"], "noncanonical_candidate_name")

    def test_id_mismatch_and_duplicate_participant_folders(self):
        self.fixture()
        (self.subject / "vid_s998_T1.avi").touch()
        wrapper = self.root / "copy" / "s999"
        wrapper.mkdir(parents=True)
        (wrapper / "vid_s999_T1.avi").touch()
        records, issues = discover(self.root)
        codes = {i["code"] for i in issues}
        self.assertIn("participant_id_mismatch_or_missing_directory", codes)
        self.assertIn("duplicate_participant_directories", codes)
        self.assertIn("ambiguous_vid", records[0]["warnings"])

    def test_symlink_and_undocumented_tasks_are_explicit(self):
        self.fixture()
        (self.subject / "vid_s999_T4.avi").touch()
        (self.subject / "bvp_s999_T4.csv").symlink_to(self.subject / "bvp_s999_T1.csv")
        records, issues = discover(self.root)
        self.assertIn("unsafe_or_symlink_source", {i["code"] for i in issues})
        self.assertIn("undocumented_task", records[-1]["warnings"])

    def test_stable_manifest_and_no_personal_information(self):
        self.fixture()
        (self.subject / "info_s999.txt").write_text("SYNTHETIC_PRIVATE_SENTINEL")
        (self.subject / "selfReportedAnx_s999.csv").write_text("SYNTHETIC_PRIVATE_SENTINEL")
        video = {"valid": True, "observed_duration_seconds": 1, "frame_rate": 25, "timing_warnings": []}
        with patch("stress_detection.manifest.inspect_video", side_effect=lambda _: copy.deepcopy(video)) as inspect:
            first = build_manifest(self.root)
            second = build_manifest(self.root)
        self.assertEqual(inspect.call_count, 6)
        self.assertEqual(first, second)
        self.assertEqual(first["validation_status"], "passed")
        self.assertNotIn("SYNTHETIC_PRIVATE_SENTINEL", str(first))
        self.assertNotIn(str(self.root), str(first))
        self.assertTrue(all(r["classification_labels"] == {} for r in first["records"]))
        self.assertTrue(all(r["synchronization"] == "unverified" for r in first["records"]))
        self.assertEqual(first["records"][0]["signals"]["bvp"]["rows"], 64)
        self.assertEqual(len(first["records"][0]["files"]["vid"]["sha256"]), 64)

    def test_generated_video_manifest_integration(self):
        self.fixture()
        for task in (1, 2, 3):
            path = self.subject / f"vid_s999_T{task}.avi"
            path.unlink()
            make_video(path)
        report = build_manifest(self.root)
        self.assertEqual(len(report["records"]), 3)
        self.assertTrue(all(r["video"]["decoded_frames"] == 3 for r in report["records"]))
        # Deliberate gaps and duration mismatch must not become a silent pass.
        self.assertEqual(report["validation_status"], "needs_review")


class SplitTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"schema_version": "1.0", "records": [
            {"recording_id": f"{p}/{t}", "participant_id": p, "task_id": t}
            for p in ("s901", "s902", "s903") for t in ("T1", "T2", "T3")]}
        self.assignments = {"schema_version": "1.0", "participants": {
            "train": ["s901"], "validation": ["s902"], "test": ["s903"]}}

    def test_all_tasks_inherit_participant_role(self):
        result = validate_splits(self.manifest, self.assignments)
        self.assertTrue(result["valid"])
        self.assertTrue(all(result["recording_roles"][f"s901/{t}"] == "train" for t in ("T1", "T2", "T3")))

    def test_overlap_and_unknown_participant_rejected(self):
        self.assignments["participants"]["test"] += ["s901", "s999"]
        result = validate_splits(self.manifest, self.assignments)
        self.assertFalse(result["valid"])
        self.assertIn("duplicate_or_overlapping_participant:s901", result["errors"])
        self.assertIn("unknown_participant:s999", result["errors"])

    def test_recording_duplicates_and_cross_split_windows_rejected(self):
        entry = {"recording_id": "s901/T1", "split": "train"}
        self.assignments["recordings"] = [entry, entry.copy()]
        self.assignments["windows"] = [{"window_id": "w1", "recording_id": "s901/T2", "split": "test"}]
        result = validate_splits(self.manifest, self.assignments)
        self.assertFalse(result["valid"])
        self.assertIn("duplicate_recordings_assignment:s901/T1", result["errors"])
        self.assertIn("participant_split_leakage:w1", result["errors"])

    def test_duplicate_window_unknown_recording_and_wrong_identity(self):
        entry = {"window_id": "w1", "recording_id": "s901/T1", "split": "train", "participant_id": "s902"}
        self.assignments["windows"] = [entry, entry.copy(), {"window_id": "w2", "recording_id": "s999/T1", "split": "test"}]
        result = validate_splits(self.manifest, self.assignments)
        self.assertFalse(result["valid"])
        self.assertIn("duplicate_windows_assignment:w1", result["errors"])
        self.assertIn("participant_id_mismatch:w1", result["errors"])
        self.assertIn("unknown_recording:s999/T1", result["errors"])

    def test_current_sample_cannot_be_assigned_final_test(self):
        manifest = {"schema_version": "1.0", "records": [{"recording_id": "s25/T1", "participant_id": "s25"}]}
        split = {"schema_version": "1.0", "participants": {"train": [], "validation": [], "test": ["s25"]}}
        result = validate_splits(manifest, split)
        self.assertFalse(result["valid"])
        self.assertIn("development_only_participant_in_test:s25", result["errors"])

    def test_unassigned_and_malformed_schema_rejected(self):
        self.assignments["participants"]["train"] = []
        self.assertFalse(validate_splits(self.manifest, self.assignments)["valid"])
        self.assertFalse(validate_splits(self.manifest, {"participants": []})["valid"])
        self.assertFalse(validate_splits(self.manifest, None)["valid"])

    def test_duplicate_manifest_recording_and_wrong_owner_rejected(self):
        self.manifest["records"].append(self.manifest["records"][0].copy())
        self.manifest["records"][1]["participant_id"] = "s902"
        result = validate_splits(self.manifest, self.assignments)
        self.assertFalse(result["valid"])
        self.assertIn("duplicate_manifest_recording:s901/T1", result["errors"])
        self.assertIn("manifest_participant_id_mismatch:s901/T2", result["errors"])


if __name__ == "__main__":
    unittest.main()
