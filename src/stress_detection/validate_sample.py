"""Validate a local UBFC-Phys sample; write private reports only under ignored data."""

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import zlib
import struct


def inspect_numeric(path: Path, columns: int, rate: int | None = None) -> dict:
    """Check headerless numeric CSV without repairing or discarding bad rows."""
    result = {"file": path.name, "rows": 0, "expected_columns": columns, "observed_column_counts": [],
              "missing": 0, "nonnumeric": 0, "nonfinite": 0,
              "malformed_rows": [], "errors": []}
    try:
        with path.open(newline="", encoding="utf-8-sig") as source:
            for index, row in enumerate(csv.reader(source, strict=True), 1):
                result["rows"] += 1
                if len(row) not in result["observed_column_counts"]:
                    result["observed_column_counts"].append(len(row))
                if len(row) != columns:
                    result["malformed_rows"].append(index)
                for value in row or [""]:
                    if not value.strip():
                        result["missing"] += 1
                        continue
                    try:
                        if not math.isfinite(float(value)):
                            result["nonfinite"] += 1
                    except ValueError:
                        result["nonnumeric"] += 1
    except (OSError, UnicodeError, csv.Error) as exc:
        result["errors"].append(type(exc).__name__)
    result["valid"] = bool(result["rows"]) and not any(
        result[key] for key in ("missing", "nonnumeric", "nonfinite", "malformed_rows", "errors")
    )
    if rate:
        result["sampling_rate_hz"] = rate
        result["nominal_duration_seconds"] = result["rows"] / rate if result["valid"] else None
        result["duration_basis"] = "sample count / documented rate; no timestamps inferred"
    return result


def missing_files(folder: Path) -> list[str]:
    """Require all task/video/reference pairs and participant-level metadata."""
    subject = folder.name
    expected = [f"{kind}_{subject}_T{task}.{suffix}"
                for task in (1, 2, 3)
                for kind, suffix in (("vid", "avi"), ("bvp", "csv"), ("eda", "csv"))]
    expected += [f"info_{subject}.txt", f"selfReportedAnx_{subject}.csv"]
    return [name for name in expected if not (folder / name).is_file()]


def inspect_info(path: Path, subject: str) -> dict:
    """Validate structure without including personal field values in the report."""
    lines = path.read_text().splitlines()
    result = {"line_count": len(lines), "values_redacted": True}
    if len(lines) != 5:
        return {**result, "valid": False}
    identifier, sex, scenario, date, time = [line.strip() for line in lines]
    result.update(identifier_matches=identifier in (subject, subject.removeprefix("s")),
                  sex_code_valid=sex in ("m", "f"), scenario_valid=scenario in ("test", "ctrl"))
    for key, value, formats in (
        ("date_format", date, ("%Y-%m-%d", "%Y_%m_%d")),
        ("time_format", time, ("%H-%M-%S", "%H_%M_%S")),
    ):
        result[key] = None
        for fmt in formats:
            try:
                datetime.strptime(value, fmt)
                result[key] = fmt
                break
            except ValueError:
                continue
    result["valid"] = all(result[k] for k in (
        "identifier_matches", "sex_code_valid", "scenario_valid", "date_format", "time_format"))
    result["documentation_date_format_matches"] = result["date_format"] == "%Y-%m-%d"
    result["documentation_time_format_matches"] = result["time_format"] == "%H-%M-%S"
    return result


def save_png(frame, path: Path) -> None:
    """Write a full-resolution RGB inspection copy without Pillow or NumPy."""
    rgb = frame.reformat(format="rgb24")
    plane = rgb.planes[0]
    pixels = bytes(plane)
    raw = b"".join(b"\0" + pixels[y * plane.line_size:y * plane.line_size + rgb.width * 3]
                   for y in range(rgb.height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    with path.open("xb") as target:
        target.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", rgb.width, rgb.height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def video_integrity(result: dict) -> dict:
    """Eligibility follows decoded data/PTS; container frame counts are metadata.

    Positive monotonic gaps remain visible for downstream window support checks.
    No timestamp/frame repair, duration alignment or count-based extrapolation.
    """
    decoded = result.get('decoded_frames', 0)
    declared = result.get('declared_frames')
    decode_ok = bool(decoded > 0 and result.get('decode_complete') and not any(
        result.get(k) for k in ('corrupt_frames', 'errors', 'decoder_error_logs', 'decoder_error_count')))
    extent = result.get('last_frame_duration_seconds')
    duration = result.get('observed_duration_seconds')
    timing_ok = (not any(result.get(k) for k in ('missing_pts', 'missing_time_base', 'duplicate_pts', 'nonmonotonic_pts'))
                 and extent is not None and math.isfinite(extent) and extent > 0
                 and duration is not None and math.isfinite(duration) and duration > 0)
    return {'camera_eligibility_policy': 'decoded-pts-v1', 'decode_integrity_passed': decode_ok,
            'timing_integrity_passed': bool(timing_ok),
            'metadata_frame_count_matches': decoded == declared if declared else None,
            'valid': bool(decode_ok and timing_ok)}


def inspect_video(path: Path, output: Path | None = None) -> dict:
    """Shared streaming inspection; optional previews for the original validator."""
    import av
    from .video_reader import VideoReader

    result = {"file": path.name, "decoded_frames": 0, "errors": [],
              "visual_check": "pending", "preview_frames": [],
              "decoder_error_logs": [], "decoder_error_count": 0}
    reader = VideoReader(path)

    def drain_logs(logs):
        for level, _, message in logs:
            if level <= av.logging.ERROR:
                result["decoder_error_count"] += 1
                if len(result["decoder_error_logs"]) < 20:
                    result["decoder_error_logs"].append(message)
        logs.clear()

    try:
        with av.logging.Capture() as logs, reader:
            targets = {0: "beginning"}
            if reader.metadata["declared_frames"] > 1:
                targets[reader.metadata["declared_frames"] // 2] = "middle"
            last = None
            for decoded in reader:
                drain_logs(logs)
                if output is not None and decoded.index in targets:
                    name = f"{path.stem}_{targets[decoded.index]}.png"
                    save_png(decoded.rgb, output / name)
                    result["preview_frames"].append({"file": name, "index": decoded.index, "pts": decoded.pts})
                # Only retain the last preview candidate, never the whole video.
                if output is not None:
                    last = decoded
            if output is not None and last is not None:
                name = f"{path.stem}_end.png"
                save_png(last.rgb, output / name)
                result["preview_frames"].append({"file": name, "index": last.index, "pts": last.pts})
        drain_logs(logs)
    except Exception as exc:
        result["errors"].append(type(exc).__name__)
        if "logs" in locals():
            drain_logs(logs)
    result.update(reader.summary())
    result.update(video_integrity(result))
    return result


def require_ignored(path: Path) -> None:
    """Prevent accidental publication of participant-derived reports/previews."""
    root = Path(__file__).resolve().parents[2]
    path = path.resolve()
    if not path.is_relative_to(root / "data/processed"):
        raise ValueError("Output must be under the project's ignored data/processed directory")
    check = subprocess.run(["git", "check-ignore", "--quiet", str(path / "validation.json")], cwd=root)
    if check.returncode:
        raise ValueError("Output is not ignored by Git")


def write_private_json(path: Path, report: dict) -> None:
    """Create a new JSON report only at a Git-ignored processed-data path."""
    path = path.resolve()
    require_ignored(path.parent)
    root = Path(__file__).resolve().parents[2]
    if subprocess.run(["git", "check-ignore", "--quiet", str(path)], cwd=root).returncode:
        raise ValueError("Report path is not ignored by Git")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as target:
        json.dump(report, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("participant_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="new directory under data/processed")
    parser.add_argument('--retain-failures', action='store_true', help='finish an audit report with failed checks; does not make those checks pass')
    args = parser.parse_args()
    folder = args.participant_dir.resolve()
    if not re.fullmatch(r"s[1-9][0-9]*", folder.name) or not folder.is_dir():
        parser.error("Expected an existing participant directory named sN")
    try:
        require_ignored(args.output)
        args.output.mkdir(parents=True, exist_ok=False)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    missing = missing_files(folder)
    report = {"missing_files": missing, "signals": [], "videos": [],
              "synchronization": "unverified; durations alone do not establish alignment"}
    for task in (1, 2, 3):
        for kind, rate in (("bvp", 64), ("eda", 4)):
            path = folder / f"{kind}_{folder.name}_T{task}.csv"
            if path.is_file():
                report["signals"].append(inspect_numeric(path, 1, rate))
    info = folder / f"info_{folder.name}.txt"
    questionnaire = folder / f"selfReportedAnx_{folder.name}.csv"
    if info.is_file():
        report["info"] = inspect_info(info, folder.name)
    if questionnaire.is_file():
        report["questionnaire"] = inspect_numeric(questionnaire, 2)
        report["questionnaire"]["valid"] &= report["questionnaire"]["rows"] == 3
        report["questionnaire"]["interpretation"] = {"rows": ["cognitive anxiety", "somatic anxiety", "self-confidence"],
                                                     "columns": ["pre-session", "post-session"]}
    try:
        import av
    except ImportError:
        parser.error("Install the inspection extra: python -m pip install -e '.[inspection]'")
    report["tools"] = {"python": sys.version.split()[0], "av": av.__version__,
                       "ffmpeg_libraries": {k: list(v) for k, v in av.library_versions.items()}}
    for task in (1, 2, 3):
        path = folder / f"vid_{folder.name}_T{task}.avi"
        if path.is_file():
            print(f"Stream-decoding task {task}...", flush=True)
            video = inspect_video(path, args.output)
            video["signal_duration_deltas_seconds"] = {}
            for kind in ("bvp", "eda"):
                signal = next((s for s in report["signals"] if s["file"] == f"{kind}_{folder.name}_T{task}.csv"), None)
                duration = video.get("observed_duration_seconds")
                if signal and signal["valid"] and duration is not None:
                    delta = duration - signal["nominal_duration_seconds"]
                    video["signal_duration_deltas_seconds"][kind] = delta
            video["duration_discrepancy"] = any(abs(d) > 1 / (video.get("frame_rate") or 1)
                                               for d in video["signal_duration_deltas_seconds"].values())
            report["videos"].append(video)
            (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    report["warnings"] = []
    if report.get("info", {}).get("valid") and not all(report["info"][k] for k in (
            "documentation_date_format_matches", "documentation_time_format_matches")):
        report["warnings"].append("Metadata separators differ from the documented date/time formats")
    if any(v.get("duration_discrepancy") for v in report["videos"]):
        report["warnings"].append("Video/reference duration discrepancy exceeds one nominal video frame")
    report["pending_checks"] = ["Human review of beginning/middle/end frames", "Video/reference synchronization"]
    report["structural_checks_passed"] = not missing and all(
        item.get("valid", False) for item in report["signals"] + report["videos"]
        + [report.get("info", {}), report.get("questionnaire", {})])
    report['validation_completed'] = True
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Private report saved. Structural checks:", "PASS" if report["structural_checks_passed"] else "FAIL")
    if not report["structural_checks_passed"] and not args.retain_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
