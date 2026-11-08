"""Validate private participant, recording and optional window split assignments."""

import argparse
import json
from pathlib import Path

from .validate_sample import write_private_json

SPLITS = ("train", "validation", "test")


def validate_splits(manifest: dict, assignments: dict) -> dict:
    """Validate assignments; never construct a split or infer a role from a window."""
    errors, warnings, roles = [], [], {}
    invalid_schema = {"valid": False, "errors": ["invalid_split_or_manifest_schema"],
                      "warnings": [], "participant_roles": {}}
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0"
            or not isinstance(manifest.get("records"), list) or not isinstance(assignments, dict)):
        return invalid_schema
    records = {}
    known = set()
    for record in manifest["records"]:
        if (not isinstance(record, dict) or not isinstance(record.get("recording_id"), str)
                or not isinstance(record.get("participant_id"), str)):
            return invalid_schema
        key, participant = record["recording_id"], record["participant_id"]
        if key.split("/", 1)[0] != participant:
            errors.append(f"manifest_participant_id_mismatch:{key}")
        known.add(participant)
        if key in records:
            errors.append(f"duplicate_manifest_recording:{key}")
        records[key] = participant
    groups = assignments.get("participants", {})
    if assignments.get("schema_version") != "1.0" or not isinstance(groups, dict) or set(groups) != set(SPLITS):
        return {"valid": False, "errors": ["invalid_split_schema"], "warnings": [], "participant_roles": {}}
    for role in SPLITS:
        if not isinstance(groups[role], list) or not all(isinstance(p, str) for p in groups[role]):
            errors.append(f"invalid_participant_list:{role}")
            continue
        if not groups[role]:
            warnings.append(f"empty_split:{role}")
        for participant in groups[role]:
            if participant not in known:
                errors.append(f"unknown_participant:{participant}")
            if participant in roles:
                errors.append(f"duplicate_or_overlapping_participant:{participant}")
            roles[participant] = role
            if participant == "s25" and role == "test":
                errors.append("development_only_participant_in_test:s25")
    for participant in sorted(known - roles.keys()):
        errors.append(f"unassigned_participant:{participant}")
    for field, identifier in (("recordings", "recording_id"), ("windows", "window_id")):
        seen = set()
        entries = assignments.get(field, [])
        if not isinstance(entries, list):
            errors.append(f"invalid_assignment_list:{field}")
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get(identifier), str):
                errors.append(f"invalid_assignment:{field}")
                continue
            key, recording, role = entry[identifier], entry.get("recording_id"), entry.get("split")
            if key in seen:
                errors.append(f"duplicate_{field}_assignment:{key}")
            seen.add(key)
            if not isinstance(recording, str) or recording not in records:
                errors.append(f"unknown_recording:{recording}")
                continue
            participant = records[recording]
            if role not in SPLITS or role != roles.get(participant):
                errors.append(f"participant_split_leakage:{key}")
            if "participant_id" in entry and entry["participant_id"] != participant:
                errors.append(f"participant_id_mismatch:{key}")
    if len(known) < 3:
        warnings.append("insufficient_participants_for_three_nonempty_splits")
    if not records:
        errors.append("empty_manifest")
    return {"valid": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)),
            "participant_roles": dict(sorted(roles.items())),
            "recording_roles": {r: roles.get(p) for r, p in sorted(records.items())},
            "cohort_sufficiency": "not established"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("assignments", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_splits(json.loads(args.manifest.read_text()), json.loads(args.assignments.read_text()))
    write_private_json(args.output, result)
    print("Split validation:", "PASS" if result["valid"] else "FAIL", "Warnings:", result["warnings"])
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
