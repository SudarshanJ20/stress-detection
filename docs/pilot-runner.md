# Resumable local UBFC-Phys pilot runner

Checked 2026-11-11. The current registered policy is `pilot-camera-v1` in
[`configs/pilot-policy-v1.json`](../configs/pilot-policy-v1.json). `stress_detection.pilot` orchestrates the existing validator,
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
the historical timestamps manifest, each full face-quality run, and each pulse
run. Those historical settings predate the registered policy; use the refreshed
selection described in [next pilot batch](next-pilot-batch.md) for current runs. For other inputs create a private selection file with the schema above.

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

### Camera eligibility policy: decoded-pts-v1

Camera eligibility follows actual decode and timing integrity. Require a complete
nonempty decode, no corrupt frames/decoder exceptions/error logs, finite positive
final-frame extent, and present strictly increasing original PTS/time bases.
Missing/duplicate/backward timing or incomplete/errorful decode remains ineligible.
Container declared-frame counts are metadata: an AVI may count an empty video
slot without containing an image there. A count mismatch alone neither proves
lost acquisition frames nor makes the surviving timestamps unreliable. Counts,
duration differences and positive PTS gaps remain visible warnings in the
validator/manifest; warnings do not silently disappear when eligibility passes.

All recordings use this same rule. Use the first original PTS as the window
origin, retain complete original-axis 30-second intervals, and never pad to the
declared count or reference duration. The unchanged pulse source/grid checks
reject windows lacking valid RGB or temporal support. A positive gap may only
support interpolation within the existing 0.15-second limit; longer gaps and
unsupported boundaries remain explicit failures in the common window inventory.
No image/frame is synthesized and timestamps are never renumbered. Timing support
alone does not establish usable RGB, pulse, acquisition clock accuracy or
video-to-wrist synchronization. Gap diagnostics now include exact original
fractions, preceding/current frame indices and PTS, and interval duration.

### Frozen bounded track restarts

The pilot now defaults to the registered bounded-reacquire policy for every
participant and task. `--track-policy contiguous` conflicts with this policy
and is refused. The standalone face command retains its legacy contiguous
default unless `--policy` or `--track-policy` is supplied. Bounded reacquisition
allows a new geometric segment after a short missing-face interruption. The same policy applies to
every selected recording, independently of pulse/reference agreement.

Require exactly one finite, valid, unclipped candidate and compatibility with
the last retained face under the existing IoU >=0.2 / normalized center shift
<=0.5 bounds. Confirm at least five consecutive candidates spanning at least
0.2 seconds, each matching the preceding candidate with IoU >=0.5 and shift
<=0.25. The last retained observation must be no more than two seconds old.
Missing or incompatible candidates reset confirmation. Multi-face ambiguity,
timestamp/geometry faults, large track discontinuities and expired absence
remain invalid and do not automatically establish a new identity.

Every pending or ambiguous observation has null landmarks/RGB and no motion
estimate. Only the final confirming frame starts a new segment; earlier frames
are never retrospectively filled. Motion and brightness-change calculations
reset at each break/restart. Segment IDs are geometric provenance, not biometric
identity. Log every acquire/break/restart/block event with original frame/PTS
in `track-events.jsonl`; all frames retain their statuses and segment ID/null
in `frames.jsonl`. Summary counts distinguish detected faces from retained
tracks. Save up to 20 event overlays as well as ordinary previews, log all
events even beyond that image limit, and inspect local overlays before accepting
a development change.

The 0.2-second confirmation leaves a gap larger than the frozen 0.15-second
pulse support limit, so windows crossing a restart retain explicit pulse
rejections. No pulse parameter, band, method or ROI is selected or retuned.
Synthetic tests cover ambiguity/timeout refusal, confirmation invalidity,
motion reset and window-specific rejection under the unchanged pulse code.

For the authorized local camera audit, a new private selection points to the
existing extracted directories, preserving the earlier roots. Use a fresh root:

```sh
.venv/bin/python -m stress_detection.pilot \
  --selection data/processed/ubfc-phys/pilot-selections/batch-01-camera-audit.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-01-camera-audit \
  --track-policy bounded-reacquire --dry-run

.venv/bin/python -m stress_detection.pilot \
  --selection data/processed/ubfc-phys/pilot-selections/batch-01-camera-audit.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-01-camera-audit \
  --track-policy bounded-reacquire
```

The selection and all detailed timing/overlay/before-after results remain
Git ignored. This is a development policy and does not establish physiological
accuracy, reliable identity continuity, or readiness for cohort expansion.

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
`manifest` points to a file named `manifest.json`; `face`, `pulse`, and
`reference` map task names to directories. `reference` verifies only the saved
independent wrist result against the current source and frozen estimator; it
does not adopt camera outputs from that directory. Reuse is opt-in. Manifest imports must contain exactly
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

Unsafe extraction, ambiguous pairing, incomplete reports or invalid participant/
reference structure stop the batch; later tasks remain explicitly blocked.
The runner requests `--retain-failures` from validation and manifest commands:
a completed audit is distinct from passed structural checks. Those flags never
change source validity. Each ineligible camera record remains a forced rejection,
while structurally valid tasks continue. Independent wrist summaries reuse
`pulse.reference_summary` with frozen settings even if the camera is ineligible.
Partial validator reports lack the final `validation_completed` marker and
cannot be promoted. The invocation retains failed task status and exits nonzero
if any camera task failed; completion of the remaining tasks does not hide it.
Per-task face/pulse/diagnostic failures likewise retain the task and allow
subsequent tasks to run. A completed pulse computation with rejected windows is still a completed
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

## Registered policy and compatibility

`--policy configs/pilot-policy-v1.json` is the default. The canonical JSON hash
is registered in `stress_detection.policy`; changing its contents under the
same version or using an unknown version fails before processing. Runtime
measurement defaults, pulse settings and timing-policy version must match.
Changing policies requires a new reviewed configuration/version and fresh
compatibility checks. No participant/task-specific policy overrides are allowed.

Every stage receipt and its signature carry the bundle version/hash and the
timing, tracking and pulse component versions; face `config.json` also carries
the stamp. Resume checks require the stamp as well as the existing input, code,
software and output hashes. Old unstamped receipts cannot silently resume.
Explicit imports must pass current stage verification: manifests need audited
timing provenance, faces need the policy stamp and exact measurements, and
pulse outputs must reproduce against the selected face frames. Dry runs and
failed candidate receipts identify rejected reuse candidates. Never edit old
receipts to give them new provenance. Reference-only imports are explicitly
verified and stamped in the new receipt while the original directory stays
unchanged. Output inventory may include historical camera files in that source
directory; these are not adopted camera results or duplicate storage.

The completed camera-continuity audit remains the evidence for the policy,
including local overlays, preserved original outputs and before/after checks.
Existing regression tests cover ambiguous/expired returns, invalid pending
frames, motion/brightness resets, and restart gaps exceeding the unchanged
0.15-second pulse limit. Registration adds tests for altered configs, conflicting
overrides, missing receipt stamps and independent reference reuse.

## Locked final participants

This engineering runner still rejects final-test participants; do not change
roles to bypass it. The [explicit final-role adapter](final-cohort-processing.md)
uses the native manifest/face/pulse functions and frozen policy with separate
role-preserving export, training on s1–s6 only, and artifact-only inference. It
never accepts a reserved questionnaire path. Model/export/prediction locks and
all original pilot artifacts remain separate.
