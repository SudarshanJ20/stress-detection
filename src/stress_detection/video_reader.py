"""Bounded-memory RGB decoding with explicit, unrepaired presentation timing."""

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class DecodedFrame:
    rgb: object  # PyAV VideoFrame, rgb24; no NumPy dependency
    index: int
    pts: int | None
    time_base: Fraction | None
    presentation_time: Fraction | None
    relative_time: Fraction | None
    fallback_time: Fraction | None
    issues: tuple[str, ...]
    corrupt: bool

    @property
    def presentation_time_seconds(self):
        return float(self.presentation_time) if self.presentation_time is not None else None


class TimingAudit:
    """Constant-size timing state; compare adjacent valid frames without repair."""

    def __init__(self, nominal_fps=None, fallback_fps=None, fallback_origin=0):
        self.nominal_fps = Fraction(str(nominal_fps)) if nominal_fps else None
        self.fallback_fps = Fraction(str(fallback_fps)) if fallback_fps is not None else None
        if self.nominal_fps is not None and self.nominal_fps <= 0:
            raise ValueError("Nominal FPS must be positive")
        if self.fallback_fps is not None and self.fallback_fps <= 0:
            raise ValueError("Fallback FPS must be positive")
        self.fallback_origin = Fraction(str(fallback_origin))
        self.first = self.last = self.previous = None
        self.first_pts = self.last_pts = None
        self.first_time_base = self.last_time_base = None
        self.first_valid_index = None
        self.counts = {k: 0 for k in ("missing_pts", "missing_time_base", "duplicate_pts",
                                      "nonmonotonic_pts", "gap_intervals", "irregular_intervals")}
        self.examples = []
        self.intervals = 0
        self.delta_sum = Fraction(0)
        self.min_delta = self.max_delta = None
        self.last_frame_duration = None

    def observe(self, index, pts, time_base, duration=None):
        issues = []
        tb = Fraction(time_base) if time_base is not None else None
        if pts is None:
            issues.append("missing_pts")
        if tb is None or tb <= 0:
            issues.append("missing_time_base")
        current = pts * tb if pts is not None and tb is not None and tb > 0 else None
        if current is not None:
            if self.first is None:
                self.first, self.first_pts, self.first_time_base = current, pts, tb
                self.first_valid_index = index
            if self.previous is not None:
                delta = current - self.previous
                self.intervals += 1
                self.delta_sum += delta
                self.min_delta = delta if self.min_delta is None else min(self.min_delta, delta)
                self.max_delta = delta if self.max_delta is None else max(self.max_delta, delta)
                if delta == 0:
                    issues.append("duplicate_pts")
                elif delta < 0:
                    issues.append("nonmonotonic_pts")
                elif self.nominal_fps:
                    expected = 1 / self.nominal_fps
                    if delta > expected * Fraction(3, 2):
                        issues.append("gap_intervals")
                    if abs(delta - expected) > max(Fraction(1, 1_000_000), expected / 100):
                        issues.append("irregular_intervals")
            self.last, self.last_pts, self.last_time_base = current, pts, tb
        # Missing timing breaks adjacency: do not invent an interval across it.
        self.previous = current
        self.last_frame_duration = duration * tb if current is not None and duration and duration > 0 else None
        for issue in issues:
            self.counts[issue] += 1
        if issues and len(self.examples) < 20:
            self.examples.append({"frame_index": index, "issues": issues})
        fallback = (self.fallback_origin + index / self.fallback_fps
                    if current is None and self.fallback_fps else None)
        relative = current - self.first if current is not None else None
        return current, relative, fallback, tuple(issues)

    def summary(self):
        def seconds(value):
            return float(value) if value is not None else None

        mean = self.delta_sum / self.intervals if self.intervals else None
        span = self.last - self.first if self.first is not None else None
        # The final frame's observed duration is separate from a nominal-rate estimate.
        observed_duration = (span + self.last_frame_duration
                             if span is not None and self.last_frame_duration is not None else None)
        return {**self.counts, "timing_examples": self.examples,
                "timestamp_source": "decoder-reported PTS; no Python timestamp reconstruction",
                "origin_pts": self.first_pts, "origin_time_base": str(self.first_time_base) if self.first_time_base else None,
                "origin_frame_index": self.first_valid_index,
                "first_pts_seconds": seconds(self.first), "last_pts_seconds": seconds(self.last),
                "last_pts": self.last_pts, "last_time_base": str(self.last_time_base) if self.last_time_base else None,
                "pts_span_seconds": seconds(span), "observed_duration_seconds": seconds(observed_duration),
                "last_frame_duration_seconds": seconds(self.last_frame_duration),
                "adjacent_timed_intervals": self.intervals,
                "spacing_min_seconds": seconds(self.min_delta), "spacing_max_seconds": seconds(self.max_delta),
                "spacing_mean_seconds": seconds(mean),
                "spacing_implied_fps": seconds(1 / mean) if mean is not None and mean > 0 else None,
                "nominal_interval_seconds": seconds(1 / self.nominal_fps) if self.nominal_fps else None,
                "fallback_fps": str(self.fallback_fps) if self.fallback_fps else None,
                "fallback_origin_seconds": seconds(self.fallback_origin) if self.fallback_fps else None}


class VideoReader:
    """Use with a context manager, particularly when breaking iteration early.

    Frames are decoded sequentially and converted to RGB at original resolution.
    The reader retains only timing aggregates and decoder state, not a frame list.
    Exhaustion/errors close the container; exiting ``with`` closes on early break.
    ``fallback_fps`` only supplies a separate synthetic time for untimed frames.
    """

    def __init__(self, path: Path, *, fallback_fps=None, fallback_origin=0):
        self.path = Path(path)
        self.fallback_fps = fallback_fps
        self.fallback_origin = fallback_origin
        self.container = self.decoder = None
        self.closed = True
        self.complete = False
        self.decoded_frames = self.corrupt_frames = 0
        self.metadata = {}
        self.audit = None

    def __enter__(self):
        import av

        if self.container is not None:
            raise RuntimeError("Reader instances cannot be reopened")
        self.container = av.open(str(self.path), mode="r")
        self.closed = False
        try:
            if len(self.container.streams.video) != 1:
                raise ValueError("Expected exactly one video stream")
            stream = self.container.streams.video[0]
            stream.codec_context.options = {"err_detect": "explode"}
            # Single decoder thread avoids an unbounded application frame queue.
            stream.codec_context.thread_count = 1
            rate = stream.average_rate
            tb = stream.time_base
            self.metadata = {"codec": stream.codec_context.name, "width": stream.width, "height": stream.height,
                             "frame_rate": float(rate) if rate else None,
                             "frame_rate_fraction": str(rate) if rate else None,
                             "declared_frames": stream.frames, "time_base": str(tb) if tb else None,
                             "stream_start_pts": stream.start_time,
                             "stream_duration_seconds": float(stream.duration * tb) if stream.duration is not None and tb else None,
                             "container_duration_seconds": self.container.duration / av.time_base if self.container.duration is not None else None}
            self.audit = TimingAudit(rate, self.fallback_fps, self.fallback_origin)
            self.decoder = self.container.decode(stream)
            return self
        except BaseException:
            self.close()
            raise

    def __iter__(self):
        if self.container is None:
            raise RuntimeError("Open VideoReader with a context manager before iterating")
        return self

    def __next__(self):
        if self.closed:
            raise StopIteration
        try:
            frame = next(self.decoder)
            index = self.decoded_frames
            timing = self.audit.observe(index, frame.pts, frame.time_base, frame.duration)
            corrupt = bool(frame.is_corrupt)
            self.decoded_frames += 1
            self.corrupt_frames += int(corrupt)
            return DecodedFrame(frame.reformat(format="rgb24"), index, frame.pts,
                                Fraction(frame.time_base) if frame.time_base is not None else None,
                                *timing[:3], timing[3], corrupt)
        except StopIteration:
            self.complete = True
            self.close()
            raise
        except BaseException:
            self.close()
            raise

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                if self.decoder is not None:
                    self.decoder.close()
            finally:
                self.container.close()

    def __exit__(self, *_):
        self.close()

    def summary(self):
        result = {**self.metadata, **(self.audit.summary() if self.audit else {}),
                  "decoded_frames": self.decoded_frames, "corrupt_frames": self.corrupt_frames,
                  "decode_complete": self.complete}
        count, rate = self.decoded_frames, self.metadata.get("frame_rate")
        result["decoded_duration_at_nominal_rate_seconds"] = count / rate if rate else None
        span = result.get("pts_span_seconds")
        result["pts_span_plus_nominal_frame_seconds"] = span + 1 / rate if span is not None and rate else None
        warnings = [key for key, count in (self.audit.counts.items() if self.audit else []) if count]
        if self.metadata.get("declared_frames") and count != self.metadata["declared_frames"]:
            warnings.append("declared/decoded frame count mismatch")
        if not self.complete:
            warnings.append("decode incomplete")
        observed = result.get("observed_duration_seconds")
        declared_duration = result.get("stream_duration_seconds")
        if observed is not None and declared_duration is not None:
            result["observed_minus_stream_duration_seconds"] = observed - declared_duration
            if abs(observed - declared_duration) > (1 / rate if rate else 1e-6):
                warnings.append("observed/declared duration mismatch")
        result["timing_warnings"] = warnings
        return result


def main():
    import argparse
    from .validate_sample import inspect_video, write_private_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect_video(args.video)
    write_private_json(args.output, result)
    print("Decoded frames:", result["decoded_frames"], "Timing warnings:", result.get("timing_warnings", []))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
