# Explicit final-cohort processing and frozen inference

Implemented 2026-11-11. The [locked v2 design](untouched-evaluation.md), participant
manifest, targets, allowlists, summaries and model settings are unchanged.
`stress_detection.independent_anxiety` and `stress_detection.final_camera_features`
provide explicit final-role support without changing historical pilot/feature/
LOPO commands or their receipts. The implementation version is
`explicit-final-support-v2`; analytical configuration SHA remains `c395c805…`.
The frozen config's earlier pipeline-status text is historical, not a changed
analytical design. No reserved participant payload was acquired or inspected.

## Completed training and validation

All **12** target/model combinations were fitted once on **s1–s6 only**, using all
six session rows. s25 remains engineering-only and does not enter any primary fit
or evaluation. Targets are raw post-session cognitive anxiety (primary) and raw
post-session somatic anxiety (secondary). The six families are training mean,
facial, BPM, combined, physical quality and missingness; no pilot winner chosen.
Ridge remains alpha 10/SVD/intercept; train-only medians/scaling and training-empty
column handling are unchanged. No score transformation/clipping/search.

The actual bundle is ignored at
`data/processed/ubfc-phys/independent-evaluation-v2/models-v2/`.
Its receipt records source code commit `1f2264c`, full computation/dependency
snapshots, the original six-session audit inventory and training roles. Model
artifacts and preprocessing are hashed. Canonical output-inventory SHA-256:
`79b9b2b67fd87a8ab0b3297e91ca502ffa674c1ec83e92bfe1cea676248ed30c`.
The first freeze is preserved at `models-v1/`; all 12 serialized model files
are byte-identical in v2, whose receipt adds the training-video identity inventory.
No fitting warnings or training-mean fallbacks occurred. Training is complete;
use validation rather than overwriting/retraining this bundle.

Deep validation verifies training data identity, means, fitted medians/scalers,
fixed parameters and the training-only Ridge normal equations. It reads only
the six development questionnaires. Ordinary inference validation checks the
saved model artifacts and hashes **without reopening any questionnaires**, even
development questionnaires. No final scores are stored in the model bundle.

**145 tests and pip check passed.** Targeted synthetic tests cover complete 120-key
prediction inventory, training/final/engineering role separation, attempted pilot/s25/training-role
imports, native camera feature equivalence, altered pulse settings, scheduled
failures, source changes, partial/duplicate batches and null/zero handling.
Training/final and cross-batch duplicate video content is rejected.
Read-denial traps reject any questionnaire or outcome-table access during export,
prediction or shallow validation, including misplaced questionnaire files in
artifact trees. A synthetic dense-timestamp camera/pulse fixture exercises the
existing measurement functions; no reserved recording is used. There are **zero
real final-cohort predictions** at this checkpoint.

## What is read, and what stays sealed

Existing development-file **contents**, not just their names, were checked:

| File | Verified structure/meaning | Export/inference use |
|---|---|---|
| `info_sN.txt` | Five fields: participant ID, sex code, assigned test/ctrl condition, date, session start time | Validate identity/structure with existing `inspect_info`; condition/date/sex are not predictors |
| `selfReportedAnx_sN.csv` | Headerless 3×2 author-computed dimension means; cognitive/somatic/confidence rows, pre/post columns, mean scale 1–4 | Development outcomes only during training; reserved files sealed and never an export/inference argument |

The README/paper interpretation is documented in [released targets](released-anxiety-targets.md).
Reserved file contents are still unknown until separate acquisition/structural
checks. Unexpected content is rejected/quarantined; a misleading filename does
not establish that a file contains only condition metadata. Local content-check
receipts for the seven exposed development participants are private in
`independent-evaluation-v2/metadata-content-verification.json`; no values enter Git.

The outcome-blind exporter reads only selected info, manifest, source-video and
face/pulse artifacts. It does not inventory raw participant directories, open
questionnaires, parse wrist references or join outcomes. Explicit source files
are hashed individually. `locked_final` is preserved in every index/window and
prediction; the native manifest's statistical split must be `test`. Final people
are never passed off as `pilot_development`.

Processing can use native manifests, face extraction and camera-only pulse with
no questionnaire present. Do not use `validate_sample` on reserved folders: that
command computes questionnaire statistics. Optional wrist diagnostics remain
separate, recording-level and outside predictors. Native pulse can omit
`--manifest/--dataset-root` to compute camera results without reading BVP.

## Outcome-blind feature export and failure policy

Private selection templates are prepared under
`data/processed/ubfc-phys/independent-evaluation-plan-v1/camera-selections/`:
ten single-participant files, five two-participant batches and `all-final.json`.
Their schema explicitly contains `id`, `role: locked_final`, `input_root`, native
manifest path and face/pulse paths for each of T1/T2/T3. No outcome path is accepted.
The locked acquisition manifest is hash-checked before every operation.

The exporter reuses `pulse.load_face_run`, `features.summarize_frames` and
`features.pulse_columns`, including the original coordinate, motion-break,
spectral-screen and 0.15 s gap rules. It verifies model/policy/software/source hashes,
complete frame/PTS identity, pulse settings and original window bounds. Pulse
failure need not erase valid facial measurements; it leaves pulse values null
and records the reason. Policy/provenance incompatibility fails the export;
it is not silently converted into a valid result.

Every participant retains 18 scheduled window slots. Failed decode/missing stages
or incomplete original intervals remain unsupported, with reasons and null
measurements. Unknown timestamps/coverage stay null, not invented zeros or nominal
PTS; pulse-absence indicators record the absence. Empty sessions remain eligible
for train-fitted imputation at prediction. No frames are invented or gaps bridged.
Session medians/coverage means and per-task counts match the locked design. The
output has one row per participant in X/index/support, plus all scheduled windows.

An export requires the completed frozen model bundle first. Receipts bind code,
policy, schema, selected source hashes and model inventory. Existing paths cannot
be overwritten; failed runs remain failed. Validate a completed output to reuse it.
For a retry, create a fresh source attempt, selection file and export directory;
do not edit files referenced by a prior successful receipt.

## Exact model and prediction commands

The completed training command was:

```sh
.venv/bin/python -m stress_detection.independent_anxiety --train \
  --plan data/processed/ubfc-phys/independent-evaluation-plan-v1/acquisition-manifest.json \
  --source-audit data/processed/ubfc-phys/session-anxiety/audit-v1 \
  --output data/processed/ubfc-phys/independent-evaluation-v2/models-v2
```

Validate it now with:

```sh
.venv/bin/python -m stress_detection.independent_anxiety --validate-models \
  --plan data/processed/ubfc-phys/independent-evaluation-plan-v1/acquisition-manifest.json \
  --output data/processed/ubfc-phys/independent-evaluation-v2/models-v2
```

`--deep-training-check` additionally reopens the development sources; omit it
for ordinary outcome-blind inference. Training reproduction requires a fresh
ignored output directory and does not replace the completed bundle.

After separately authorized acquisition and native camera processing, the
complete-cohort export and prediction commands are:

```sh
.venv/bin/python -m stress_detection.final_camera_features \
  --plan data/processed/ubfc-phys/independent-evaluation-plan-v1/acquisition-manifest.json \
  --models-run data/processed/ubfc-phys/independent-evaluation-v2/models-v2 \
  --selection data/processed/ubfc-phys/independent-evaluation-plan-v1/camera-selections/all-final.json \
  --output data/processed/ubfc-phys/independent-evaluation-v2/exports/all-v1

.venv/bin/python -m stress_detection.independent_anxiety --predict \
  --plan data/processed/ubfc-phys/independent-evaluation-plan-v1/acquisition-manifest.json \
  --models-run data/processed/ubfc-phys/independent-evaluation-v2/models-v2 \
  --export data/processed/ubfc-phys/independent-evaluation-v2/exports/all-v1 \
  --output data/processed/ubfc-phys/independent-evaluation-v2/predictions/all-v1

.venv/bin/python -m stress_detection.independent_anxiety --validate-predictions \
  --plan data/processed/ubfc-phys/independent-evaluation-plan-v1/acquisition-manifest.json \
  --output data/processed/ubfc-phys/independent-evaluation-v2/predictions/all-v1
```

Prediction has **no outcome argument or joining function**. The result must have
`all_scheduled_predictions_locked: true`, exactly 120 unique participant/target/
model keys, unchanged 12-model hashes and a completed output-hash receipt before
reserved questionnaire release is considered. It contains no truth/condition
column. No scores or performance metrics are generated by prediction.
External-history uncertainty is a separate unresolved eligibility gate, not
resolved by this artifact-lock flag. Outcome evaluation/release is a later step.

## Sequential batches and storage

Process one participant at a time. Export singles or the prepared pair selections
into fresh `exports/batch-01-v1` through `batch-05-v1` roots. A partial prediction
can use `--allow-partial-batch` for 12/24/etc predictions; it explicitly returns
`all_scheduled_predictions_locked: false` and **does not permit cohort unblinding**.
For the final 120-key lock, supply all nonoverlapping exports via repeated
`--export` arguments and omit `--allow-partial-batch`. Missing, duplicate,
training/engineering or overlapping participants are rejected. The private
`processing-commands-final-support-v2.md` has concrete batch/native recipes.

The storage recheck after model freezing measured approximately **551.68GiB free**.
The existing conservative archive fallback remains **535.99GiB**, including
145.99GiB for the prior advertised ZIP budget, 200GiB provisional extraction,
50GiB outputs, 40GiB sequential workspace and 100GiB reserve. About 15.69GiB remains
beyond those allowances. These are estimates, not verified new archive sizes.
Resident original archives/outputs already reduce free space and are not charged
again. Actual central-directory sizes, safe paths, CRC integrity and current
remaining space must be checked before every extraction. Stop if they will not fit.

Full archive originals and prior successful/failed results are retained. Byte
hashing/CRC for sealed transport is allowed; no score parsing/statistics/viewing.
No automatic deletion or re-download is required by this adapter. Individual-file
access remains login-gated/unverified: check small info delivery first, then prefer
separate videos/companions if offered; questionnaires stay in sealed custody.
The private exact filenames are in `independent-evaluation-plan-v1/next-files.md`.

No reserved payloads were downloaded. Exposure outside reviewed local records is
still unconfirmed; the final cohort is **not certified untouched**. This support
implements the locked protocol-transfer experiment, not ordinary webcam/live
anxiety validation or removal of task/recording confounds.
