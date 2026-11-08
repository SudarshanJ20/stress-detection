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


def inspect_video(path: Path, output: Path) -> dict:
    """Stream-decode every frame, detecting exceptions, corruption, and error logs."""
    import av

    result = {"file": path.name, "decoded_frames": 0, "corrupt_frames": 0,
              "missing_pts": 0, "nonmonotonic_pts": 0, "errors": [],
              "visual_check": "pending", "preview_frames": []}
    try:
        with av.logging.Capture() as logs, av.open(str(path)) as container:
            if len(container.streams.video) != 1:
                raise ValueError("Expected exactly one video stream")
            stream = container.streams.video[0]
            stream.codec_context.options = {"err_detect": "explode"}
            rate = float(stream.average_rate) if stream.average_rate else None
            duration = float(stream.duration * stream.time_base) if stream.duration is not None else None
            result.update(codec=stream.codec_context.name, width=stream.width, height=stream.height,
                          frame_rate=rate, declared_frames=stream.frames,
                          stream_duration_seconds=duration,
                          container_duration_seconds=container.duration / av.time_base if container.duration else None,
                          time_base=str(stream.time_base))
            targets = {0: "beginning", max(0, stream.frames // 2): "middle"} if stream.frames else {0: "beginning"}
            first = previous = last = None
            last_frame = None
            for index, frame in enumerate(container.decode(stream)):
                result["decoded_frames"] += 1
                result["corrupt_frames"] += int(frame.is_corrupt)
                if frame.pts is None:
                    result["missing_pts"] += 1
                else:
                    current = float(frame.pts * frame.time_base)
                    if previous is not None and current <= previous:
                        result["nonmonotonic_pts"] += 1
                    if first is None:
                        first = current
                    previous = last = current
                if index in targets:
                    name = f"{path.stem}_{targets[index]}.png"
                    save_png(frame, output / name)
                    result["preview_frames"].append({"file": name, "index": index, "pts": frame.pts})
                last_frame = frame
            if last_frame is not None:
                name = f"{path.stem}_end.png"
                save_png(last_frame, output / name)
                result["preview_frames"].append({"file": name, "index": result["decoded_frames"] - 1, "pts": last_frame.pts})
            result["first_pts_seconds"] = first
            result["last_pts_seconds"] = last
            result["decoded_duration_at_nominal_rate_seconds"] = result["decoded_frames"] / rate if rate else None
            result["pts_span_plus_nominal_frame_seconds"] = last - first + 1 / rate if first is not None and rate else None
        result["decoder_error_logs"] = [message for level, _, message in logs if level <= av.logging.ERROR]
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    result["valid"] = (result["decoded_frames"] > 0 and not any(result.get(k) for k in (
        "corrupt_frames", "errors", "decoder_error_logs"))
        and (not result.get("declared_frames") or result["decoded_frames"] == result["declared_frames"]))
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("participant_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="new directory under data/processed")
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
                duration = video.get("decoded_duration_at_nominal_rate_seconds")
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
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Private report saved. Structural checks:", "PASS" if report["structural_checks_passed"] else "FAIL")
    if not report["structural_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
