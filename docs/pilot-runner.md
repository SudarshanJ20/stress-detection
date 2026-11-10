# Resumable local UBFC-Phys pilot runner

Checked 2026-11-10. `stress_detection.pilot` orchestrates the existing validator,
participant-scoped manifest, face-quality, pulse and diagnostic commands in
separate processes. It downloads nothing and trains nothing. Pulse `Settings`
remain frozen, with no CLI threshold overrides. Synchronization remains
unverified; camera/BVP comparisons use independent recording-level medians and
coverages only. No offset is estimated and no method/ROI is selected by agreement.

## Explicit selection and roles

Supply `--selection` with a private JSON file. Relative paths resolve from the
working directory; the commands below assume the repository root. It requires
`schema_version: "1.0"`, `final_test_cohort: "unassigned"`, a nonempty
`selection_reason`, `pilot_selected_before_quality: true`, and a nonempty ordered
`participants` list. Each entry contains `id`, `role`, and exactly one input:
`directory` (an existing `sN` directory) or `zip` (a local archive).

Only `development_only` is allowed for s25; additional participants must use
`pilot_development`. All three tasks are always scheduled and inherit that
participant's role. At most two additional people are permitted per batch. These
are exploratory engineering roles, not a training/validation/test allocation.
No final test participant is selected or processed by this runner. The selection
attestation applies to new pilot participants, not the already inspected s25.
Do not use signal quality to choose, replace or reorder the proposed batch.

For example, the proposed first new batch's private file has this structure:

```json
{
  "schema_version": "1.0",
  "final_test_cohort": "unassigned",
  "pilot_selected_before_quality": true,
  "selection_reason": "First two eligible numeric participant IDs; chosen before signal-quality inspection; availability and scenario checks pending login.",
  "participants": [
    {"id": "s1", "role": "pilot_development", "zip": "data/raw/UBFC-Phys-archives/s1.zip"},
    {"id": "s2", "role": "pilot_development", "zip": "data/raw/UBFC-Phys-archives/s2.zip"}
  ]
}
```

The runner freezes the normalized selection in its output root before executing
stages. Changing membership, order, roles, inputs or reuse paths requires a new
root. A dry run also detects disagreement with an existing frozen selection.

## Exact local commands

The private selection files used for this check already exist locally:
`data/processed/ubfc-phys/pilot-selections/s25-smoke.json` and
`batch-01-proposed.json`. They are intentionally absent from Git. The smoke
selection identifies the existing s25 directory and explicit reuse candidates:
the saved timestamps manifest, each full face-quality run, and each frozen pulse
run. For other inputs create a private selection file with the schema above.

```sh
.venv/bin/python -m stress_detection.pilot \
  --selection data/processed/ubfc-phys/pilot-selections/s25-smoke.json \
  --output data/processed/ubfc-phys/pilot-runner/s25-smoke \
  --dry-run

.venv/bin/python -m stress_detection.pilot \
  --selection data/processed/ubfc-phys/pilot-selections/s25-smoke.json \
  --output data/processed/ubfc-phys/pilot-runner/s25-smoke
```

Repeat the execution command unchanged to resume. The dry run writes no runner
state and performs no extraction or stage subprocess. It lists selected IDs,
roles and tasks, verifies local files and numeric structure, checks pairing and
free space, and shows each stage as `resume`, `verify-import`, or requiring work.
Downstream decisions awaiting new extraction/manifest outputs remain explicit.
Hashing and read-only reuse verification can take time, even in dry-run mode.
Output contains private file fingerprints; redirect it only to ignored paths.

After a separately authorized download, the first new batch can be checked and
executed with:

```sh
.venv/bin/python -m stress_detection.pilot \
  --selection data/processed/ubfc-phys/pilot-selections/batch-01-proposed.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-01 \
  --dry-run

.venv/bin/python -m stress_detection.pilot \
  --selection data/processed/ubfc-phys/pilot-selections/batch-01-proposed.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-01
```

The current proposed-batch dry run is expected to fail because its ZIPs have
not been downloaded. It does not fetch them. Availability/scenario-driven
revisions must be recorded before looking at signal quality, in a new selection.

Optional `--model` and `--model-config` point to the existing local model and
provenance JSON; the model's checksum must match. Defaults use the repository's
existing MediaPipe bundle. No model download is attempted. Optional storage
allowances default to `--reserve-gib 100 --workspace-gib 40
--outputs-gib-per-participant 5`. These are conservative planning allowances,
not measured dataset sizes or enforced maximum output quotas. They can be
increased without changing pulse settings. Retained failed attempts consume
space; inspect disk use before retrying large failed stages.

## ZIP and storage lifecycle

Preflight inspects ZIP central-directory member names, declared uncompressed
size, duplicates including case collisions, path traversal, symlinks, encryption,
compression support, participant ID and the documented file set. It currently
accepts canonical `sN/file` layout and stored/Deflate members. Other wrappers or
extra files are rejected for explicit inspection; they are never silently
renamed. Central-directory checks do not prove CRC integrity. Extraction reads
every member fully, checks CRC via `zipfile`, verifies sizes and the unchanged
archive hash, and creates files exclusively. The archive is retained.

ZIP extraction goes into that participant's new extraction attempt under the
ignored runner root. It is a copy of the original content, not a transformed
video. Previous extraction attempts remain intact; there is no automatic cleanup.
Existing directory inputs are processed in place, read-only. Participants and
tasks execute sequentially; other participants in the same dataset directory
are excluded by the manifest's `--participant` option.

Dry-run disk requirements are the sum of all not-yet-verified ZIP extractions,
the per-participant output allowance, workspace allowance and OS reserve.
Already resident ZIPs and directory inputs already reduce measured free space,
so they are not added again as *new* required bytes. Stage boundaries recheck
free space. Archives, extracted inputs and outputs on different filesystems need
separate capacity planning; this runner checks the destination filesystem and
does not initiate transfers between them.

## Verification, receipts and failures

Every stage gets a unique immutable attempt directory with an atomic
`receipt.json`, start/end times, input/settings/code/software/model provenance,
command log where a subprocess ran, output path and content hashes. A process
interruption leaves `running`; caught failures become `failed`. Partial command
outputs are preserved. Only a successful command plus stage-specific completion
checks can create a `completed` receipt. Completed-with-warnings face runs are
allowed only after full decode; partial face runs are refused.

Resume requires a completed receipt, the exact stage signature and every
output's current content hash. Inputs are content-hashed again; file size or
mtime alone never proves reuse. New settings, source/code/library changes,
deleted files, partial status or same-size corruption invalidate the receipt.
The runner tries a new attempt and retains the old one. A filesystem lock
prevents simultaneous executions against one root. Do not edit inputs while a
run is active; participant inputs are checked again after processing.

Existing outputs can be explicitly offered in an entry's `reuse` object:
`manifest` points to a file named `manifest.json`; `face` and `pulse` map task
names to directories. Reuse is opt-in. Manifest imports must contain exactly
the selected person's tasks and match current source hashes/rates/completion.
Face imports require full original timing, frame counts, matching source,
model, settings and software. Pulse imports reproduce current camera decisions,
traces, timing, reference results and summaries with frozen code/settings.
Imported directories are referenced and hashed, never edited or copied.

Legacy validator reports lack source fingerprints, so they cannot be imported
safely. The runner performs a fresh validation once and can resume its own
fingerprinted receipt thereafter. Diagnostics run afresh against the selected
manifest and pulse runs. Saved stage signatures include current source hashes;
editing runner code invalidates earlier receipts conservatively.

Structural validation, manifest or extraction failure stops the batch; all later
participants/tasks remain in the invocation summary as blocked. Per-task
face/pulse/diagnostic failures retain that task and allow subsequent tasks to
run. A completed pulse computation with rejected windows is still a completed
stage; zero acceptance is not a process failure. Failures never become success
because output files happened to be present.

## Private summaries and pilot gates

Each execution creates a new `invocations/<id>/` with `plan.json`, atomic
`status.json`, `summary.json` and `windows.jsonl`. All are ignored. Summaries
include every scheduled task, face detection/tracking and region coverage,
camera acceptance by method/region, independent BVP acceptance, candidate
band-edge annotations, rejection reasons, current stage runtime, available
historical face runtime, and logical storage bytes. Reused verification time
is distinguished from the original stage execution time. Historical failed or
interrupted receipts remain visible.

The window inventory retains all successful-stage rows, including rejected
windows. A failed stage with a verified schedule produces explicit forced
rejections. If video timing or a malformed/missing signal prevents establishing
a schedule, its count is **unknown**, not zero or an invented nominal duration;
the task remains in the denominator audit. Diagnostic edge flags annotate
estimates without changing the fixed acceptance screen. Recording-level
comparisons are kept separate from window inventories and never labeled paired
errors. Source archives, external imported outputs and runner-owned bytes are
reported separately; shared references must not be added as duplicated storage.

`development_tasks`/`development_summary` contain s25 exclusively.
`pilot_tasks`/`pilot_summary` exclude it. Group coverage includes participant
denominators and equal-participant averages; unknown denominators are flagged.
An empty pilot does not become evidence from the development participant.
Runtime measures operational stage/verification cost, not the later protocol's
formal repeated CPU benchmark.

Before training, require the [protocol](research-protocol.md) participant split
and leakage checks, structural/provenance integrity, complete failure inventory,
documented units and missingness, development-justified quality handling, and
feasible grouped validation. Audit per-task/region/scenario rejection and edge
prevalence without reference-guided selection. Resolve synchronization and
reference validity before paired physiological evaluation. The
[frozen audit](pulse-diagnostics.md) remains applicable; no training readiness
or multi-participant performance claim follows from the s25 exercise.

## Recommended first new batch and budget

Use **s1 and s2**, all three tasks each, as an availability-conditional first
engineering batch. This is a reproducible numeric-ID choice made before signal
inspection, excludes s25 and the previously reported filename-issue candidates,
and is not a claim of scenario balance or statistical sufficiency. The
[official DataPort listing](https://ieee-dataport.org/open-access/ubfc-phys-2),
rechecked 2026-11-10, advertises `s1.zip` at **13.8 GB** and `s2.zip` at
**13.34 GB**; total **27.14 GB**. Its restricted `sN_zip` folders may offer a
finer-grained route, but individual-file delivery remains unverified.

For preliminary planning only, reserve **20 GiB extracted per participant** and
**5 GiB outputs per participant**. Extraction size is unknown until the ZIP
central directories can be inspected; the existing sample is not an upper
bound. Depending on the host's GB convention, archives consume roughly
25.3–27.1 GiB. Retaining both archives, both extracted participants and outputs
therefore budgets about **75.3–77.1 GiB**, plus the protocol's **40 GiB active
workspace** and **100 GiB OS reserve**: approximately **215–218 GiB free before
acquisition**. This is a provisional allowance, not a guarantee. Replace the
extraction allowance with actual declared sizes before extraction and increase
it if necessary. Preserve archives and failed attempts in updated projections.

After login, verify free-account access and any current terms, actual archive
byte sizes and filenames, successful delivery/resume behavior, whether the
restricted folders expose individual original files, and available scenario
metadata. Record scenario balance or imbalance before quality inspection;
do not replace candidates because their pulse looks poor. Do not assume HTTP
range support, selective remote ZIP extraction or payment-free access from the
generic modal alone. No login, terms acceptance, additional download or training
was performed in this task.

## Local workflow verification

The local s25 exercise covered all tasks. Initial execution imported the
verified manifest and full face/pulse outputs, performed fresh validation, and
generated current diagnostics. After the final implementation changes, an
unchanged dry run marked every stage resumable; execution resumed all 11 stages
without stage subprocesses. Earlier attempts from implementation checks remain
preserved with their original code signatures. Pilot summaries remained empty;
s25 results stayed in the separate development section.

A separate, explicitly labeled local interruption probe created an incomplete
diagnostic output, confirmed it could not resume as success, then completed
fresh diagnostics using the existing s25 inputs and resumed the verified result.
The failed probe output remains private. This was a lifecycle test, not an
observed participant/sensor failure. A read-only preflight of the original local
ZIP checked declared extraction size and paths without extracting another copy.
The proposed new-batch preflight failed explicitly on the unacquired ZIPs.

All 79 synthetic tests and `pip check` passed. Tests include content/settings
changes, same-size corruption, failed/partial/interrupted stages, immutable
imports, selection/role restrictions, dry-run space checks, all-stage resume,
failure denominators, unsafe/duplicate ZIP members and CRC failure. The
diagnostic plotter now handles recordings without complete reference windows;
the pulse estimator and frozen settings are unchanged. Per-participant values,
runtime/storage reports and plots remain under ignored local paths.
