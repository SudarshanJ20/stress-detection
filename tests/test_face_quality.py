"""Synthetic geometry/RGB/timestamps and mocked detections; no participant fixtures."""

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import cv2
import numpy as np

from stress_detection.face_measurements import (EYES, FACE_OVAL, MOUTH, REGIONS,
    SingleFaceTrack, face_masks, normalized_motion, polygon_mask, quality_measurements, region_rgb)
from stress_detection.face_quality import FrameAnalyzer, TimestampBridge, run_video
from test_video_reader import make_video


def synthetic_face():
    points = np.tile([0.5, 0.5, 0.0], (478, 1))
    def ellipse(ids, center, radii):
        for index, angle in zip(ids, np.linspace(-np.pi / 2, 3 * np.pi / 2, len(ids), endpoint=False)):
            points[index, :2] = np.array(center) + np.array(radii) * [np.cos(angle), np.sin(angle)]
    ellipse(FACE_OVAL, (.5, .5), (.4, .45))
    ellipse(EYES[0], (.36, .40), (.07, .025))
    ellipse(EYES[1], (.64, .40), (.07, .025))
    ellipse(MOUTH, (.5, .7), (.12, .035))
    ellipse(REGIONS["cheek_image_left"], (.3, .57), (.08, .06))
    ellipse(REGIONS["cheek_image_right"], (.7, .57), (.08, .06))
    points[REGIONS["forehead"], :2] = [[.5, .07], [.7, .12], [.68, .22], [.62, .27],
                                              [.5, .28], [.38, .27], [.32, .22], [.3, .12]]
    return points


def frame(index, timestamp):
    tb = Fraction(1, 10000)
    return SimpleNamespace(index=index, pts=int(timestamp / tb) if timestamp is not None else None,
                           time_base=tb, presentation_time=timestamp,
                           presentation_time_seconds=float(timestamp) if timestamp is not None else None,
                           issues=(), corrupt=False)


class MaskMeasurementTests(unittest.TestCase):
    def test_polygon_boundary_clipping_and_degeneracy(self):
        mask = polygon_mask([[-5, -5], [5, -5], [5, 5], [-5, 5]], (10, 10))
        self.assertEqual(cv2.countNonZero(mask), 36)
        self.assertEqual(cv2.countNonZero(polygon_mask([[20, 20], [25, 20], [20, 25]], (10, 10))), 0)
        self.assertEqual(cv2.countNonZero(polygon_mask([[1, 1], [1, 1], [1, 1]], (10, 10))), 0)

    def test_regions_exclude_eyes_and_mouth(self):
        _, _, _, masks, exclusion = face_masks(synthetic_face(), (256, 256))
        for mask in masks.values():
            self.assertGreater(cv2.countNonZero(mask), 32)
            self.assertEqual(cv2.countNonZero(cv2.bitwise_and(mask, exclusion)), 0)

    def test_clipped_face_masks_are_safe(self):
        face = synthetic_face()
        face[:, 0] -= .4
        _, box, _, masks, _ = face_masks(face, (128, 128))
        self.assertTrue(box["clipped"])
        self.assertEqual(box["xyxy_pixels"][0], 0)
        self.assertTrue(all(mask.shape == (128, 128) for mask in masks.values()))

    def test_raw_rgb_mean_and_invalid_regions(self):
        rgb = np.full((10, 10, 3), [10, 100, 240], dtype=np.uint8)
        original = rgb.copy()
        mask = np.full((10, 10), 255, np.uint8)
        self.assertEqual(region_rgb(rgb, mask)["mean_rgb"], [10, 100, 240])
        self.assertFalse(region_rgb(rgb, np.zeros_like(mask))["valid"])
        invalid = rgb.astype(float)
        invalid[0, 0] = np.nan
        self.assertIsNone(region_rgb(invalid, mask)["mean_rgb"])
        np.testing.assert_array_equal(rgb, original)

    def test_brightness_clipping_and_sharpness_definitions(self):
        mask = np.full((10, 10), 255, np.uint8)
        dark = quality_measurements(np.zeros((10, 10, 3), np.uint8), mask)
        bright = quality_measurements(np.full((10, 10, 3), 255, np.uint8), mask)
        self.assertEqual(dark["dark_fraction"], 1)
        self.assertEqual(bright["saturated_fraction"], 1)
        self.assertEqual(dark["laplacian_variance"], 0)

    def test_motion_uses_face_size_and_elapsed_seconds(self):
        previous = np.array([[0, 0], [10, 10]], dtype=float)
        current = previous + [10, 0]
        box = [0, 0, 100, 100]
        self.assertAlmostEqual(normalized_motion(previous, current, box, box, 2), .05)
        self.assertAlmostEqual(normalized_motion(previous * 2, current * 2, [0, 0, 200, 200], [0, 0, 200, 200], 2), .05)
        self.assertIsNone(normalized_motion(previous, current, box, box, 0))


class TrackingTimingTests(unittest.TestCase):
    def test_missing_face_is_not_filled_or_reacquired(self):
        track = SingleFaceTrack()
        points = synthetic_face()
        self.assertIsNotNone(track.accept([points], 0, 256, 256)[0])
        self.assertEqual(track.accept([], .04, 256, 256)[1], "missing_face")
        self.assertEqual(track.accept([points], .08, 256, 256)[1], "track_lost_no_reacquisition")

    def test_multiple_faces_and_large_spatial_jump(self):
        points = synthetic_face()
        track = SingleFaceTrack()
        track.accept([points], 0, 256, 256)
        self.assertIsNone(track.accept([points, points.copy()], .04, 256, 256)[0])
        self.assertTrue(track.lost)
        track = SingleFaceTrack()
        track.accept([points], 0, 256, 256)
        moved = points.copy()
        moved[:, 0] += .7
        self.assertEqual(track.accept([moved], .04, 256, 256)[1], "track_continuity_failed")

    def test_nonzero_origin_rounding_and_collision(self):
        bridge = TimestampBridge()
        self.assertEqual(bridge.convert(Fraction(7, 2)), 0)
        self.assertEqual(bridge.convert(Fraction(7001, 2000)), 1)  # half-up at 0.5 ms
        with self.assertRaisesRegex(ValueError, "collision"):
            bridge.convert(Fraction(35006, 10000))
        with self.assertRaisesRegex(ValueError, "nonmonotonic"):
            bridge.convert(Fraction(3))

    def test_analyzer_marks_missing_multiple_and_timing_failures(self):
        rgb = np.full((256, 256, 3), 100, np.uint8)
        detector = Mock()
        detector.detect.side_effect = [[synthetic_face()], [], [synthetic_face(), synthetic_face()]]
        analyzer = FrameAnalyzer()
        first, _ = analyzer.analyze(frame(0, Fraction(5)), rgb, detector)
        missing, _ = analyzer.analyze(frame(1, Fraction(504, 100)), rgb, detector)
        multiple, _ = analyzer.analyze(frame(2, Fraction(508, 100)), rgb, detector)
        bad_time, _ = analyzer.analyze(frame(3, None), rgb, detector)
        self.assertEqual(first["pts"], 50000)
        self.assertEqual(first["api_timestamp_ms"], 0)
        self.assertIsNone(first["detection_score"])
        self.assertEqual(missing["face_count"], 0)
        self.assertEqual(multiple["face_count"], 2)
        self.assertIsNone(missing["landmarks_normalized_xyz"])
        self.assertIsNone(multiple["landmarks_normalized_xyz"])
        self.assertEqual(bad_time["face_status"], "missing_original_timestamp")
        self.assertIsNone(bad_time["face_count"])
        self.assertEqual(detector.detect.call_count, 3)

    def test_collision_never_bumps_api_timestamp(self):
        rgb = np.full((256, 256, 3), 100, np.uint8)
        detector = Mock()
        detector.detect.return_value = [synthetic_face()]
        analyzer = FrameAnalyzer()
        analyzer.analyze(frame(0, Fraction(0)), rgb, detector)
        row, _ = analyzer.analyze(frame(1, Fraction(1, 10000)), rgb, detector)
        self.assertEqual(row["face_status"], "integer_timestamp_collision")
        self.assertIsNone(row["api_timestamp_ms"])
        self.assertEqual(detector.detect.call_count, 1)


class RunStatusTests(unittest.TestCase):
    def setUp(self):
        private_root = Path(__file__).resolve().parents[1] / "data/processed"
        self.temp = tempfile.TemporaryDirectory(dir=private_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / "synthetic.mkv"
        make_video(self.video)
        self.model = self.root / "synthetic.task"
        self.model.write_bytes(b"synthetic model fixture, not real weights")
        self.info = {"sha256": hashlib.sha256(self.model.read_bytes()).hexdigest()}

    def test_partial_run_and_model_closure(self):
        detector = Mock()
        detector.detect.return_value = [synthetic_face()]
        factory = Mock(return_value=detector)
        output = self.root / "partial"
        result = run_video(self.video, output, self.model, self.info, max_frames=1, detector_factory=factory)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(json.loads((output / "status.json").read_text())["status"], "partial")
        detector.close.assert_called_once()
        with self.assertRaises(FileExistsError):
            run_video(self.video, output, self.model, self.info, detector_factory=factory)

    def test_failed_initialization_has_failed_summary(self):
        output = self.root / "failed"
        with self.assertRaises(RuntimeError):
            run_video(self.video, output, self.model, self.info, detector_factory=Mock(side_effect=RuntimeError("synthetic")))
        self.assertEqual(json.loads((output / "summary.json").read_text())["status"], "failed")
        self.assertEqual(json.loads((output / "status.json").read_text())["status"], "failed")

    def test_cleanup_failure_is_not_reported_as_success(self):
        detector = Mock()
        detector.detect.return_value = [synthetic_face()]
        detector.close.side_effect = RuntimeError("synthetic cleanup failure")
        output = self.root / "cleanup-failed"
        result = run_video(self.video, output, self.model, self.info, max_frames=1,
                           detector_factory=Mock(return_value=detector))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(json.loads((output / "status.json").read_text())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
