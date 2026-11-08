"""Build a private deterministic UBFC-Phys manifest using the shared validator."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from .validate_sample import inspect_numeric, inspect_video, write_private_json

SCHEMA_VERSION = "1.0"
TASK_CONDITIONS = {"T1": "rest", "T2": "speech", "T3": "arithmetic"}
PATTERN = re.compile(r"^(vid|bvp|eda)_(s[1-9][0-9]*)_(T[0-9]+)(.*?)\.(avi|csv)$", re.I)
PARTICIPANT = re.compile(r"s[1-9][0-9]*")


def discover(root: Path):
    """Pair by directory participant and filename task, retaining every candidate.

    Repeated wrappers/copies and filename-directory ID mismatches are errors;
    neither 'first match wins' nor automatic renaming is allowed.
    """
    root = root.resolve()
    participants, grouped, issues = {}, {}, []
    for folder in sorted(root.rglob("*")):
        if folder.is_dir() and not folder.is_symlink() and PARTICIPANT.fullmatch(folder.name):
            participants.setdefault(folder.name, []).append(folder.relative_to(root).as_posix())
    for subject, folders in sorted(participants.items()):
        if len(folders) > 1:
            issues.append({"code": "duplicate_participant_directories", "participant_id": subject, "paths": folders})
        for task in TASK_CONDITIONS:
            grouped[(subject, task)] = {kind: [] for kind in ("vid", "bvp", "eda")}
    for path in sorted(root.rglob("*")):
        if not path.is_file() and not path.is_symlink():
            continue
        match = PATTERN.fullmatch(path.name)
        if not match:
            if path.name.lower().startswith(("vid_", "bvp_", "eda_")):
                issues.append({"code": "unrecognized_recording_filename", "path": path.relative_to(root).as_posix()})
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            issues.append({"code": "unsafe_or_symlink_source", "path": relative})
            continue
        kind, filename_subject, task, suffix, extension = match.groups()
        kind, filename_subject, task = kind.lower(), filename_subject.lower(), task.upper()
        folder_subject = next((name for name in reversed(path.relative_to(root).parts[:-1])
                               if PARTICIPANT.fullmatch(name)), None)
        if folder_subject is None or folder_subject != filename_subject:
            issues.append({"code": "participant_id_mismatch_or_missing_directory", "path": relative})
            continue
        expected_extension = "avi" if kind == "vid" else "csv"
        if extension.lower() != expected_extension:
            issues.append({"code": "wrong_file_type", "path": relative})
            continue
        if suffix:
            issues.append({"code": "noncanonical_candidate_name", "path": relative})
        grouped.setdefault((folder_subject, task), {k: [] for k in ("vid", "bvp", "eda")})[kind].append(relative)
    records = []
    for (subject, task), candidates in sorted(grouped.items()):
        warnings = []
        for kind, paths in candidates.items():
            if not paths:
                warnings.append(f"missing_{kind}")
            elif len(paths) > 1:
                warnings.append(f"ambiguous_{kind}")
        if task not in TASK_CONDITIONS:
            warnings.append("undocumented_task")
        records.append({"recording_id": f"{subject}/{task}", "participant_id": subject, "task_id": task,
                        "task_condition": TASK_CONDITIONS.get(task), "classification_labels": {},
                        "synchronization": "unverified", "split_role": "development_only" if subject == "s25" else "unassigned",
                        "candidates": candidates, "warnings": warnings})
    return records, issues


def fingerprint(path: Path, relative: str):
    before = path.stat()
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Source changed while hashing")
    return {"path": relative, "bytes": after.st_size, "sha256": digest}


def build_manifest(root: Path):
    """Inspect unique pairs, recording failures rather than selecting a candidate."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Dataset root must be an existing directory")
    records, issues = discover(root)
    report = {"schema_version": SCHEMA_VERSION, "dataset": "UBFC-Phys", "records": records,
              "discovery_issues": issues, "synchronization": "unverified",
              "task_conditions_source": "Official UBFC-Phys READ_ME (see docs/dataset-access.md)",
              "split_status": "no evaluation split assigned"}
    for record in records:
        print("Inspecting", record["recording_id"], flush=True)
        record["files"], record["signals"] = {}, {}
        pairing_ok = not record["warnings"]
        for kind, paths in record["candidates"].items():
            if len(paths) != 1:
                continue
            relative = paths[0]
            path = root / relative
            before = path.stat()
            try:
                record["files"][kind] = fingerprint(path, relative)
                if kind == "vid":
                    video = inspect_video(path)
                    video.pop("file", None)
                    # Keep structured diagnostics, not decoder text that might embed absolute paths.
                    video.pop("decoder_error_logs", None)
                    record["video"] = video
                    record["warnings"].extend(video.get("timing_warnings", []))
                    if not video["valid"]:
                        record["warnings"].append("video_validation_failed")
                else:
                    signal = inspect_numeric(path, 1, {"bvp": 64, "eda": 4}[kind])
                    signal.pop("file", None)
                    record["signals"][kind] = signal
                    if not signal["valid"]:
                        record["warnings"].append(f"{kind}_validation_failed")
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError("Source changed during inspection")
            except (OSError, ValueError) as exc:
                record["warnings"].append(f"{kind}_inspection_error:{type(exc).__name__}")
        video = record.get("video", {})
        # Compare measured endpoint extent only when all original timestamps are usable.
        measured = video.get("observed_duration_seconds") if video.get("valid") else None
        if measured is None:
            record["warnings"].append("video_duration_comparison_unavailable")
        record["duration_comparisons"] = {}
        for kind, signal in record["signals"].items():
            reference = signal.get("nominal_duration_seconds")
            delta = measured - reference if measured is not None and reference is not None else None
            record["duration_comparisons"][kind] = {
                "observed_video_minus_nominal_reference_seconds": delta,
                "reference_time_basis": "sample count / documented rate; origin and synchronization unverified"}
            if delta is not None and abs(delta) > 1 / (video.get("frame_rate") or 1):
                record["warnings"].append(f"video_{kind}_duration_discrepancy")
        record["warnings"] = sorted(set(record["warnings"]))
        record["validation_status"] = "passed" if (
            pairing_ok and not record["warnings"] and video.get("valid")
            and len(record["signals"]) == 2 and all(s["valid"] for s in record["signals"].values())
        ) else "needs_review"
    report["validation_status"] = "passed" if records and not issues and all(
        r["validation_status"] == "passed" for r in records) else "needs_review"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--splits", type=Path, help="optional private participant split JSON; never auto-generated")
    args = parser.parse_args()
    # Check output privacy and overwrite protection before expensive decoding.
    from .validate_sample import require_ignored
    require_ignored(args.output.parent)
    if args.output.exists():
        parser.error("Output exists; choose a new manifest path")
    report = build_manifest(args.dataset_root)
    if args.splits:
        from .validate_splits import validate_splits
        split = json.loads(args.splits.read_text())
        result = validate_splits(report, split)
        report["split_validation"] = result
        if result["valid"]:
            for record in report["records"]:
                record["split_role"] = result["participant_roles"][record["participant_id"]]
            report["split_status"] = "validated assignments; not evidence of cohort sufficiency"
        else:
            report["validation_status"] = "needs_review"
    write_private_json(args.output, report)
    print("Manifest records:", len(report["records"]), "Status:", report["validation_status"])
    if report["validation_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
