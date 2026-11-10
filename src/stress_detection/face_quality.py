"""Stream pretrained landmarks, geometric RGB regions and basic quality measurements."""

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import time

import cv2
import numpy as np

from .face_measurements import (REGIONS, SingleFaceTrack, face_masks,
                                normalized_motion, quality_measurements, region_rgb)
from .manifest import fingerprint
from .validate_sample import require_ignored, write_private_json
from .video_reader import VideoReader

DEFAULT_CONFIG = {"min_pixels": 32, "dark_threshold": 20, "saturated_threshold": 235,
                  "exclusion_margin_fraction": 0.015, "num_faces": 2,
                  "min_face_detection_confidence": 0.5, "min_face_presence_confidence": 0.5,
                  "min_tracking_confidence": 0.5, "min_track_iou": 0.2,
                  "max_track_center_shift": 0.5, "max_track_gap_seconds": 0.5,
                  'reacquire_enabled': False, 'reacquire_min_frames': 5, 'reacquire_stable_seconds': .2,
                  'reacquire_max_absence_seconds': 2., 'reacquire_min_iou': .5,
                  'reacquire_max_center_shift': .25}


class TimestampBridge:
    """Explicit first-PTS origin subtraction and rational nearest-ms half-up rounding."""

    def __init__(self):
        self.origin = self.last_original = self.last_ms = None

    def convert(self, timestamp):
        if timestamp is None:
            raise ValueError("missing_original_timestamp")
        if self.last_original is not None and timestamp <= self.last_original:
            raise ValueError("duplicate_or_nonmonotonic_original_timestamp")
        self.last_original = timestamp
        if self.origin is None:
            self.origin = timestamp
        timestamp_ms = int(((timestamp - self.origin) * 1000 + Fraction(1, 2)) // 1)
        if self.last_ms is not None and timestamp_ms <= self.last_ms:
            raise ValueError("integer_timestamp_collision")
        self.last_ms = timestamp_ms
        return timestamp_ms


class MediaPipeDetector:
    def __init__(self, model, config):
        import mediapipe as mp

        self.mp = mp
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model),
                                             delegate=mp.tasks.BaseOptions.Delegate.CPU),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=config["num_faces"],
            min_face_detection_confidence=config["min_face_detection_confidence"],
            min_face_presence_confidence=config["min_face_presence_confidence"],
            min_tracking_confidence=config["min_tracking_confidence"],
            output_face_blendshapes=False, output_facial_transformation_matrixes=False)
        self.detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def detect(self, rgb, timestamp_ms):
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self.detector.detect_for_video(image, timestamp_ms)
        return [np.array([[p.x, p.y, p.z] for p in face], dtype=float) for face in result.face_landmarks]

    def close(self):
        self.detector.close()


class FrameAnalyzer:
    def __init__(self, config=None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        c = self.config
        self.bridge = TimestampBridge()
        self.track = SingleFaceTrack(c["min_track_iou"], c["max_track_center_shift"], c["max_track_gap_seconds"],
            reacquire=c['reacquire_enabled'], **{k: c[k] for k in (
                'reacquire_min_frames', 'reacquire_stable_seconds', 'reacquire_max_absence_seconds',
                'reacquire_min_iou', 'reacquire_max_center_shift')})
        self.previous = None

    def analyze(self, frame, rgb, detector):
        c = self.config
        row = {"frame_index": frame.index, "pts": frame.pts,
               "time_base": str(frame.time_base) if frame.time_base is not None else None,
               "presentation_time_fraction": str(frame.presentation_time) if frame.presentation_time is not None else None,
               "presentation_time_seconds": frame.presentation_time_seconds,
               "timestamp_issues": list(frame.issues), "api_timestamp_ms": None,
               "face_count": None, "detection_available": False,
               "detection_score": None, "tracking_score": None,
               "landmarks_normalized_xyz": None, "face_box": None, "measurements": None,
               "motion_face_sizes_per_second": None, "brightness_change_per_second": None}
        self.track.last_event = None
        masks = {}
        try:
            if frame.corrupt:
                raise ValueError("corrupt_frame")
            timestamp_ms = self.bridge.convert(frame.presentation_time)
            row["api_timestamp_ms"] = timestamp_ms
            row["api_origin_original_time_fraction"] = str(self.bridge.origin)
            faces = detector.detect(rgb, timestamp_ms)
            row["face_count"] = len(faces)
            row["face_count_at_capacity"] = len(faces) >= c["num_faces"]
            row["detection_available"] = bool(faces)
            selected, status = self.track.accept(faces, float(frame.presentation_time), rgb.shape[1], rgb.shape[0])
            row["face_status"] = status
            if selected is not None:
                if self.track.last_event and self.track.last_event['type'] in ('acquire', 'restart'):
                    self.previous = None
                xy, box, face, masks, _ = face_masks(selected, rgb.shape[:2], c["exclusion_margin_fraction"])
                measurements = quality_measurements(rgb, face, c["min_pixels"], c["dark_threshold"], c["saturated_threshold"])
                row.update(landmarks_normalized_xyz=selected.tolist(), face_box=box, measurements=measurements)
                row["regions"] = {name: region_rgb(rgb, mask, c["min_pixels"]) for name, mask in masks.items()}
                if measurements["valid"]:
                    if self.previous is not None:
                        prior_xy, prior_box, prior_brightness, prior_time = self.previous
                        dt = float(frame.presentation_time - prior_time)
                        row["motion_face_sizes_per_second"] = normalized_motion(prior_xy, xy[:468], prior_box,
                                                                               box["xyxy_pixels"], dt)
                        row["brightness_change_per_second"] = (measurements["brightness"] - prior_brightness) / dt
                    self.previous = (xy[:468], box["xyxy_pixels"], measurements["brightness"], frame.presentation_time)
                else:
                    self.previous = None
            else:
                self.previous = None
        except ValueError as exc:
            # Only our fixed diagnostic codes are retained, never arbitrary exception contents.
            code = str(exc)
            row["face_status"] = code if code in {
                "missing_original_timestamp", "duplicate_or_nonmonotonic_original_timestamp",
                "integer_timestamp_collision", "corrupt_frame"} else "invalid_geometry_or_detector_value_error"
            self.track.invalidate(row['face_status'])
            self.previous = None
        except RuntimeError:
            row["face_status"] = "detector_runtime_error"
            self.track.invalidate(row['face_status'])
            self.previous = None
        if "regions" not in row:
            row["regions"] = {name: {"valid": False, "pixel_count": 0, "mean_rgb": None,
                                      "reason": row["face_status"]} for name in REGIONS}
        row['track_segment_id'] = self.track.segment_id if row['landmarks_normalized_xyz'] is not None else None
        row['track_event'] = self.track.last_event
        return row, masks


def save_overlay(rgb, row, masks, output):
    overlay = rgb.copy()
    colors = [(255, 100, 0), (0, 220, 100), (80, 120, 255)]
    for (name, mask), color in zip(masks.items(), colors):
        overlay[mask != 0] = (0.7 * overlay[mask != 0] + 0.3 * np.array(color)).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, color, 1)
    points = row["landmarks_normalized_xyz"]
    if points is not None:
        height, width = rgb.shape[:2]
        for x, y, _ in points[:468]:
            if 0 <= x < 1 and 0 <= y < 1:
                cv2.circle(overlay, (round(x * width), round(y * height)), 1, (255, 255, 0), -1)
    cv2.putText(overlay, f"frame {row['frame_index']} {row['face_status']}", (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 0, 0), 2)
    if not cv2.imwrite(str(output), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)):
        raise OSError("Overlay could not be saved")


def run_video(input_path, output, model, model_info, *, max_frames=None, manifest=None,
              detector_factory=MediaPipeDetector, measurement_config=None):
    """A new private run directory owns all outputs; summary/status mark partial failures."""
    started = time.perf_counter()
    measurements = {**DEFAULT_CONFIG, **(measurement_config or {})}
    output, input_path, model = Path(output), Path(input_path), Path(model)
    require_ignored(output)
    if not input_path.is_file() or not model.is_file():
        raise ValueError("Input video and local model must exist")
    with model.open("rb") as model_file:
        actual_sha = hashlib.file_digest(model_file, "sha256").hexdigest()
    if actual_sha != model_info["sha256"]:
        raise ValueError("Model checksum mismatch")
    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames must be positive")
    source = fingerprint(input_path, input_path.name)
    recording_id = None
    if manifest is not None:
        matches = [r for r in manifest["records"] if r.get("files", {}).get("vid", {}).get("sha256") == source["sha256"]]
        if len(matches) != 1:
            raise ValueError("Input does not identify exactly one manifest recording")
        recording_id = matches[0]["recording_id"]
        source["path"] = matches[0]["files"]["vid"]["path"]
    output.mkdir(parents=True, exist_ok=False)
    configuration = {"schema_version": "1.0", "source": source, "recording_id": recording_id,
                     "model": model_info, "measurements": measurements,
                     "regions_landmark_indices": REGIONS, "max_frames": max_frames,
                     "software": {p: version(p) for p in ("mediapipe", "numpy", "opencv-contrib-python", "av")},
                     "python": platform.python_version(), "architecture": platform.machine(),
                     "delegate": "CPU", "synchronization": "unverified",
                     "scores": "Detection/tracking scores not exposed by FaceLandmarkerResult; thresholds are not scores",
                     "api_time": "round_half_up(1000*(original_time-first_valid_original_time)); collisions are skipped, not repaired",
                     "identity_policy": ('bounded confirmed geometric segments; no biometric identity claim'
                         if measurements['reacquire_enabled'] else 'single contiguous geometric track; no automatic reacquisition or biometric identity claim')}
    write_private_json(output / "config.json", configuration)

    def status(value):
        temporary = output / "status.tmp"
        temporary.write_text(json.dumps({"status": value}) + "\n")
        temporary.replace(output / "status.json")

    status("running")
    summary = {"status": "running", "processed_frames": 0, "detected_frames": 0, "single_face_frames": 0,
               "missing_face_frames": 0, "multiple_face_frames": 0, "tracked_frames": 0,
               "valid_region_frames": {name: 0 for name in REGIONS}, "synchronization": "unverified",
               "overlays_visual_check": "pending", "preview_files": []}
    counts = Counter()
    event_counts = Counter()
    event_previews = 0
    analyzer = FrameAnalyzer(measurements)
    detector = None
    reader = VideoReader(input_path)
    process_start = None
    try:
        detector = detector_factory(model, measurements)
        with reader, (output / "frames.jsonl").open("x") as frames_file, (output / 'track-events.jsonl').open('x') as events_file:
            extent = min(reader.metadata["declared_frames"] or (max_frames or 1), max_frames or reader.metadata["declared_frames"] or 1)
            previews = {0, extent // 2, extent - 1}
            process_start = time.perf_counter()
            for frame in reader:
                rgb = frame.rgb.to_ndarray(format="rgb24")
                row, masks = analyzer.analyze(frame, rgb, detector)
                frames_file.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")
                summary["processed_frames"] += 1
                summary["detected_frames"] += int(row["detection_available"])
                summary["single_face_frames"] += int(row["face_count"] == 1)
                summary["missing_face_frames"] += int(row["face_count"] == 0)
                summary["multiple_face_frames"] += int(row["face_count"] is not None and row["face_count"] > 1)
                summary["tracked_frames"] += int(row['track_segment_id'] is not None)
                counts[row["face_status"]] += 1
                if row['track_event']:
                    event_counts[row['track_event']['type']] += 1
                    event = {k: row[k] for k in ('frame_index', 'pts', 'time_base', 'presentation_time_fraction', 'track_event')}
                    events_file.write(json.dumps(event, allow_nan=False) + '\n')
                    if event_previews < 20:
                        name = f"overlay_event_{frame.index:06d}_{row['track_event']['type']}.png"
                        save_overlay(rgb, row, masks, output / name)
                        summary['preview_files'].append(name)
                        event_previews += 1
                for name, region in row["regions"].items():
                    summary["valid_region_frames"][name] += int(region["valid"])
                if frame.index in previews:
                    name = f"overlay_{frame.index:06d}.png"
                    save_overlay(rgb, row, masks, output / name)
                    summary["preview_files"].append(name)
                if summary["processed_frames"] % 1000 == 0:
                    print("Processed", summary["processed_frames"], "frames", flush=True)
                if max_frames is not None and summary["processed_frames"] >= max_frames:
                    break
        summary["status"] = "completed" if reader.complete else "partial"
        if reader.complete and summary["tracked_frames"] != summary["processed_frames"]:
            summary["status"] = "completed_with_warnings"
    except BaseException as exc:
        summary["status"] = "failed"
        summary["failure_type"] = type(exc).__name__
        raise
    finally:
        if detector is not None:
            try:
                detector.close()
            except Exception as exc:
                summary["status"] = "failed"
                summary["cleanup_failure_type"] = type(exc).__name__
        summary["reader"] = reader.summary()
        summary["frame_status_counts"] = dict(sorted(counts.items()))
        summary['track_event_counts'] = dict(sorted(event_counts.items()))
        summary['track_segments'] = analyzer.track.segment_id
        summary["processing_seconds"] = time.perf_counter() - process_start if process_start is not None else None
        summary["total_seconds"] = time.perf_counter() - started
        n = summary["processed_frames"]
        summary["detection_coverage"] = summary["detected_frames"] / n if n else None
        summary["tracked_coverage"] = summary["tracked_frames"] / n if n else None
        summary["region_coverage"] = {k: v / n if n else None for k, v in summary["valid_region_frames"].items()}
        summary["approx_frames_per_second"] = n / summary["processing_seconds"] if summary["processing_seconds"] else None
        write_private_json(output / "summary.json", summary)
        status(summary["status"])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new run directory under ignored data/processed")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, default=Path("configs/face-landmarker.json"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--max-frames", type=int, help="explicit partial smoke run")
    parser.add_argument('--track-policy', choices=('contiguous', 'bounded-reacquire'), default='contiguous')
    args = parser.parse_args()
    result = run_video(args.input, args.output, args.model, json.loads(args.model_config.read_text()),
                       max_frames=args.max_frames, manifest=json.loads(args.manifest.read_text()) if args.manifest else None,
                       measurement_config={'reacquire_enabled': args.track_policy == 'bounded-reacquire'})
    print(json.dumps(result, indent=2))
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
