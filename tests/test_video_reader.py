"""Tiny generated media and synthetic timing only."""

from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import av

from stress_detection.video_reader import TimingAudit, VideoReader
from stress_detection.validate_sample import inspect_video


def make_video(path, pts=(50, 51, 54)):
    """Lossless synthetic frames with nonzero origin and an intentional gap."""
    with av.open(str(path), "w") as container:
        stream = container.add_stream("ffv1", rate=25)
        stream.width = stream.height = 16
        stream.pix_fmt = "bgr0"
        stream.time_base = Fraction(1, 25)
        for value in pts:
            frame = av.VideoFrame(16, 16, "rgb24")
            for plane in frame.planes:
                plane.update(bytes(plane.buffer_size))
            frame.pts = value
            frame.time_base = Fraction(1, 25)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


class TimingTests(unittest.TestCase):
    def test_gap_example_preserves_exact_original_location(self):
        audit = TimingAudit(Fraction(25))
        audit.observe(0, 10, Fraction(1, 25), 1)
        audit.observe(1, 12, Fraction(1, 25), 1)
        gap = audit.examples[0]
        self.assertEqual(gap['previous_frame_index'], 0)
        self.assertEqual(gap['previous_pts'], 10)
        self.assertEqual(gap['pts'], 12)
        self.assertEqual(gap['previous_time_fraction'], '2/5')
        self.assertEqual(gap['original_time_fraction'], '12/25')
        self.assertEqual(gap['interval_fraction'], '2/25')

    def test_exact_fraction_and_nonzero_origin(self):
        audit = TimingAudit(Fraction(30000, 1001))
        first = audit.observe(0, 300, Fraction(1001, 30000), 1)
        second = audit.observe(1, 301, Fraction(1001, 30000), 1)
        self.assertEqual(first[0], Fraction(1001, 100))
        self.assertEqual(second[1], Fraction(1001, 30000))
        self.assertEqual(audit.first_pts, 300)
        self.assertEqual(audit.first_time_base, Fraction(1001, 30000))

    def test_missing_duplicate_backwards_and_missing_time_base(self):
        audit = TimingAudit(25)
        for index, pts in enumerate((10, 10, 9, None, 12)):
            audit.observe(index, pts, Fraction(1, 25))
        audit.observe(5, 13, None)
        self.assertEqual(audit.counts["duplicate_pts"], 1)
        self.assertEqual(audit.counts["nonmonotonic_pts"], 1)
        self.assertEqual(audit.counts["missing_pts"], 1)
        self.assertEqual(audit.counts["missing_time_base"], 1)
        self.assertEqual(audit.intervals, 2)  # no fabricated interval over missing PTS

    def test_fallback_is_separate_and_opt_in(self):
        audit = TimingAudit(25)
        self.assertEqual(audit.observe(2, None, Fraction(1, 25))[:3], (None, None, None))
        audit = TimingAudit(25, fallback_fps=10, fallback_origin=7)
        value, relative, fallback, _ = audit.observe(2, None, Fraction(1, 25))
        self.assertIsNone(value)
        self.assertIsNone(relative)
        self.assertEqual(fallback, Fraction(36, 5))
        self.assertIsNone(audit.observe(3, 100, Fraction(1, 25))[2])
        with self.assertRaises(ValueError):
            TimingAudit(fallback_fps=0)

    def test_pts_window_assignment_differs_from_index_over_fps(self):
        audit = TimingAudit(25)
        audit.observe(0, 500, Fraction(1, 25))
        _, relative, _, _ = audit.observe(1, 1300, Fraction(1, 25))
        self.assertEqual(relative // 30, 1)
        self.assertEqual(Fraction(1, 25) // 30, 0)
        self.assertEqual(audit.counts["gap_intervals"], 1)

    def test_diagnostics_are_bounded(self):
        audit = TimingAudit()
        for index in range(1000):
            audit.observe(index, None, None)
        self.assertEqual(len(audit.examples), 20)
        self.assertEqual(audit.counts["missing_pts"], 1000)


class ReaderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "synthetic.mkv"
        make_video(self.path)

    def test_rgb_stream_preserves_decoded_timing(self):
        with VideoReader(self.path) as reader:
            frames = list(reader)  # intentionally only three tiny synthetic frames
        self.assertEqual(len(frames), 3)
        self.assertEqual([f.presentation_time for f in frames], [Fraction(2), Fraction(51, 25), Fraction(54, 25)])
        self.assertEqual([f.index for f in frames], [0, 1, 2])
        self.assertTrue(all(f.rgb.format.name == "rgb24" for f in frames))
        self.assertEqual(frames[0].relative_time, 0)
        self.assertEqual(reader.summary()["gap_intervals"], 1)
        self.assertTrue(reader.complete)
        self.assertTrue(reader.closed)

    def test_early_break_closes_native_container(self):
        native = av.open(str(self.path))
        spy = Mock(wraps=native)
        spy.streams, spy.duration = native.streams, native.duration
        with patch("av.open", return_value=spy):
            with VideoReader(self.path) as reader:
                for _ in reader:
                    break
            spy.close.assert_called_once()
            self.assertFalse(reader.complete)
            self.assertTrue(reader.closed)

    def test_consumer_exception_closes_native_container(self):
        native = av.open(str(self.path))
        spy = Mock(wraps=native)
        spy.streams, spy.duration = native.streams, native.duration
        with patch("av.open", return_value=spy):
            with self.assertRaisesRegex(RuntimeError, "consumer"):
                with VideoReader(self.path) as reader:
                    next(reader)
                    raise RuntimeError("consumer")
        spy.close.assert_called_once()

    def test_decoder_failure_closes_container(self):
        native = av.open(str(self.path))
        spy = Mock(wraps=native)
        spy.streams, spy.duration = native.streams, native.duration

        def broken_decoder(*_):
            yield next(native.decode(video=0))
            raise ValueError("synthetic decode failure")

        spy.decode.side_effect = broken_decoder
        with patch("av.open", return_value=spy):
            with self.assertRaisesRegex(ValueError, "synthetic"):
                with VideoReader(self.path) as reader:
                    for _ in reader:
                        pass
        spy.close.assert_called_once()
        self.assertFalse(reader.complete)

    def test_existing_inspection_reuses_reader(self):
        result = inspect_video(self.path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["decoded_frames"], 3)
        self.assertEqual(result["first_pts_seconds"], 2)
        self.assertEqual(result["preview_frames"], [])


if __name__ == "__main__":
    unittest.main()
