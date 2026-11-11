# Original-window baseline feature tables

`stress_detection.features` derives raw, camera-only features from compatible
`pilot-camera-v1` face/pulse runs. Contract:
[`window-features-v1.json`](../configs/window-features-v1.json). It does not decode
videos again, rerun the detector, change pulse/tracker settings, align wrist
signals, fit preprocessing, select features from outcomes or train models.
These are geometric/task-discrimination inputs, not validated emotion, blink,
psychological-stress or physiological measurements.

## Inventory and column groups

One row represents participant / task / original complete 30-second interval.
Use the first original PTS as origin; intervals are half-open and nonoverlapping.
Retain original rational origin and explicit start/end seconds, trailing extent,
all rejected estimates and every scheduled row. No padding, frame synthesis,
window shifting, interpolation for facial features or pulse-based row deletion.
The pilot selection schedules s1–s6, three tasks and six intervals each: **108
rows**. s25 is a separate **18-row development-only** run. Neither is a final
evaluation cohort or a train/validation/final-test allocation.

| Column group | Prefix / storage | Meaning and model use |
|---|---|---|
| Identifiers and provenance | `id_*` in `windows.jsonl` and contrast `index.jsonl` | Participant/role, recording/task/window keys, original bounds, paths, source hashes, policy/schema versions and compatibility basis. Never predictors. |
| Facial behaviour | `beh_*` | Eight numeric nullable geometric summaries below. |
| Camera pulse | `cam_*` | Six separate Green/POS × forehead/image-left/image-right BPM columns, each with saved status and rejection reason. Only BPM is in the pulse-only predictor list. |
| Video quality and missingness | `q_*` | Camera-derived coverage, pixel/geometry/timing proxies, feature-support reasons and pulse quality/missingness. Numeric columns have explicit control/selector lists; reason strings never enter X. |
| Task labels | `label_condition`; contrast `target` in index only | T1=`rest`, T2=`speech`, T3=`arithmetic`. Experimental condition, not measured stress. |
| Reference-only diagnostics | `ref_*` in **separate** `reference-recordings.jsonl` | Independent cached wrist BVP diagnostics and EDA sample-count/rate/duration metadata. Recording grain, no join to camera intervals. Never predictors. |

`windows.jsonl` contains no wrist BVP/EDA values or wrist acceptance flags.
Each contrast's `X.jsonl` contains **only** the 57 numeric nullable camera-derived
columns in `schema.model_columns`; IDs, paths, timestamps, task identifiers,
labels, recording order and reference diagnostics are absent. Its separate
`index.jsonl` preserves grouping/provenance and binary targets in identical line
order. Use the named feature lists, rather than all 57 columns, for each baseline.
Never append metadata or the ordinal line position as a predictor.

## Facial geometry and support

Read the existing retained 478-point mesh. Convert projected coordinates to
pixels as `(x * width, y * height)` before measuring Euclidean distances; ignore
z. This handles nonsquare image aspect. Normalize each aperture by its own
projected corner distance, not by a learned participant/window/cohort baseline.
No 3D pose correction or identity normalization is performed.

| Per-frame proxy | Definition using mesh indices |
|---|---|
| Mouth opening | distance(13,14) / distance(61,291) |
| Eye A opening | distance(159,145) / distance(33,133) |
| Eye B opening | distance(386,374) / distance(263,362) |
| Combined eye opening | Mean of both valid eye ratios; both are required |

Require one retained face/segment, 478 finite landmarks, selected aperture points
inside the image, and a corner distance greater than `1e-8` pixels (numerical
degeneracy guard). Mouth and eyes have independent support. Local ratios are
dimensionless projected geometry: pose, expression, glasses, occlusion and mesh
errors can affect them. They are not action-unit, emotion or blink detectors.

The eight behaviour columns are:

- Mouth opening: mean, population standard deviation, 95th percentile.
- Combined eye opening: mean, population standard deviation, 10th percentile.
- Facial motion: median and 95th percentile in face sizes/second.

Motion reuses and verifies the existing landmark-derived scalar: RMS displacement
of the first 468 projected points, divided by the mean of the two face-box sizes
(`sqrt(pixel area)`), divided by original elapsed seconds. Recompute it from the
adjacent saved landmarks to verify provenance. Require adjacent decoded retained
frames in the **same interval and track segment**, neither box clipped, positive
elapsed time at most **0.15 s**, and a finite original motion value. Exclude
acquire/restart/break transitions. No previous-window motion, missing/pending
track observations or long gaps are bridged. Global head movement and expression
are combined; there is no separate validated pose estimate.

A statistic requires **at least two valid samples and at least 90% support**.
Aperture denominators are all decoded frames in the interval; motion denominators
are its `n-1` adjacent decoded-frame pairs. Unsupported families have all their
statistics null, with coverage and a support reason. Missing intervals remain
rows with null features. Means/quantiles use the observed samples, unweighted by
time, with NumPy linear quantiles. A supported distribution can span a marked
missing gap; it does not assert a continuous waveform. Facial summaries can
therefore remain supported when pulse fails its stricter complete-grid test.
These support requirements belong to the **feature contract**, not a tracker or
pulse-policy change. Never retune them per participant/task.

## Pulse and quality

Preserve each existing Green/POS estimate independently for all three regions.
An accepted estimate must retain its finite BPM and fixed spectral-screen status;
a rejection must retain **null BPM** and its exact reason. Candidate peaks from
failed spectra are not substituted. Verify a complete six-variant inventory,
unique keys, and exact original start/end bounds. Pulse `Settings` and the
0.15-second support limit remain unchanged. No method/region is selected using
reference agreement.

Quality is aggregated over the same decoded-frame intervals:

- Detection/retained-track/multiple-face/clipped-face fractions; no-frame flag;
  mouth/eye/motion/brightness-change valid fractions; break-event fraction.
- Original timestamp-issue fraction and fraction of adjacent timed transitions
  ending in the interval with gap >0.15 s (including a leading transition from
  the preceding interval). No absolute timestamp or nominal recording order is
  a model input.
- Existing face-mask brightness mean/std (uint8 gray levels), dark/saturated
  fraction means, Laplacian-variance mean (gray-level squared), face-area mean,
  and guarded absolute brightness-change median (gray levels/second).
- Each region's valid RGB fraction and mean pixel area / image area.
- Separately identifiable camera-pulse missing flags, spectral peak fractions,
  and accepted-estimate near-band-edge flags, using existing diagnostic semantics.

Pixel/area/brightness summary statistics require the same 90% and two-sample
support; fractions remain descriptive even when summary values are null.
Brightness change uses the guarded motion transitions. Geometric RGB masks are
not validated skin segmentation, and these are raw proxies, not a composite or
calibrated quality score. Pulse peak fractions are not calibrated confidence.

## Prespecified predictor lists and confound checks

`feature-lists.json` and the committed schema define these fixed lists:

| List | Columns | Later purpose |
|---|---:|---|
| `facial_only` | 8 | Geometric behaviour baseline |
| `pulse_only` | 6 | All fixed camera pulse variants |
| `ordinary_fusion` | 14 | Facial + pulse, without quality weighting |
| `motion_only` | 2 | Head-motion/expression confound check |
| `fusion_without_motion` | 12 | Shared-motion removal ablation |
| `video_quality_only` | 25 | Camera quality/availability confound control, without pulse-derived quality |
| `missingness_only` | 17 | Coverage/failure indicators only; no BPM or pixel-intensity values |
| `quality_and_missingness` | 43 | Secondary camera quality list including pulse-derived quality |

Fixed family definitions are not fitted feature selection. Quality and
missingness may identify experimental task or acquisition artifacts. Later
quality-only/missingness-only and motion-only classifiers must be reported as
confound controls, not evidence of stress measurement. Keep video-only quality
separate from pulse-derived quality and retain all scheduled denominators.

Define **both** contrasts: rest-vs-speech and rest-vs-arithmetic. Each pilot
contrast contains **72 rows**, with rest target 0 and its own positive condition
target 1; do not pool speech and arithmetic. The s25 contrasts each contain 12
rows in the separate development root. Participant IDs in index files are for
grouped folds only. Later learned normalization, imputation, feature selection,
all-null-column handling, model tuning and calibration must fit inside training
folds, using participant-held-out outer evaluation and participant-grouped inner
selection. No whole-cohort standardization, participant baseline subtraction,
zero-filling or data-driven column removal is performed here.

## Reference isolation and compatibility

`reference-recordings.jsonl` copies the independent cached BVP summary, including
its own nominal-axis diagnostics, **once per recording**, not per video interval.
EDA values/statistics are not derived or copied; only structural metadata is
retained there. Neither file nor any wrist-quality oracle is available to X or
the webcam application. Equal nominal durations do not establish synchronization.
No camera-minus-wrist window feature, waveform join, offset fit or paired error
is produced. Keep later comparisons at recording level while alignment is
unverified; see the [protocol gate](research-protocol.md#pulse-reference-synchronization-gate--pending).

The selection names explicit source summary files and roles. The command checks
completed receipts, stored signatures and output inventories; matching numeric
policies and core code; model/source/frame/pulse pairing; original file hashes;
full decode/timing; and NumPy/Python provenance. New runs need the registered
bundle stamp. Historical s1/s2 audited runs additionally require the existing
explicit compatibility attestation matching the policy, source summary and
participants. Those old receipts are never rewritten or silently stamped.
Adding this command does not force another face/pulse run: import checks compare
the relevant unchanged computation components, not unrelated added modules.

## Commands and saved artifacts

Run from the repository root. Private selections are already prepared at
`data/processed/ubfc-phys/feature-selections/pilot-s1-s6-v1.json` and
`development-s25-v1.json`. Each has schema version 1.0, `cohort` (`pilot` or
`development`), `expected_rows`, `final_test_cohort: "unassigned"`, and explicit
participant entries (`id`, `role`, `summary`; `legacy_compatibility` for s1/s2).
The pilot forbids s25; development permits only s25/development_only. Each source
must contain all three tasks. No participant is selected by feature availability.

```sh
.venv/bin/python -m stress_detection.features --print-schema

.venv/bin/python -m stress_detection.features \
  --selection data/processed/ubfc-phys/feature-selections/pilot-s1-s6-v1.json \
  --output data/processed/ubfc-phys/window-features/pilot-s1-s6-v1-final

.venv/bin/python -m stress_detection.features \
  --selection data/processed/ubfc-phys/feature-selections/development-s25-v1.json \
  --output data/processed/ubfc-phys/window-features/development-s25-v1-final

.venv/bin/python -m stress_detection.features \
  --validate-run data/processed/ubfc-phys/window-features/pilot-s1-s6-v1-final

.venv/bin/python -m stress_detection.features \
  --validate-run data/processed/ubfc-phys/window-features/development-s25-v1-final
```

A build requires a **new ignored output directory**; it refuses to overwrite.
For reproduction use the same selection and a fresh output path. Artifacts:
`windows.jsonl`, separate `reference-recordings.jsonl`, two contrast directories
(each `X.jsonl` + `index.jsonl`), `schema.json`, `feature-lists.json`,
`validation.json` and `receipt.json`. Nulls are JSON `null`, never NaN/Infinity.
Tables are sorted participant/task/window for reproducibility; positional order
is not a predictor. The validation report contains every column's missing count
and support/rejection reasons by participant/task, plus original schedules and
trailing extent. The receipt stores source/output hashes, policy/schema/code/
runtime versions and completion status. Interrupted/failed builds retain their
partial files and cannot validate as completed runs.

`--validate-run` checks all saved output hashes, unique keys/counts/bounds/nulls,
contrast pairing/labels, role separation, and current schema, policy, computation
code and numerical-runtime compatibility. It does not rehash all originals;
a fresh build repeats the original-source checks. Preserve older outputs when
changing the feature contract/version. No incompatible output is silently reused.

Synthetic tests cover aspect/scale geometry, degenerate/missing landmarks,
90% support boundaries, segment/gap/window motion exclusion, saved-motion
reproduction, incomplete/duplicate pulse inventories, failed-null semantics,
wrong boundaries/labels/provenance/roles, forbidden predictor columns, contrast
reference isolation and incomplete/corrupt/incompatible receipts. Participant
tables, missingness reports and reproduction checks remain Git ignored.

The validated pilot table is suitable for an **exploratory participant-held-out
baseline** with explicit missingness and both required contrasts. Six people
provide exploratory engineering evidence; a final evaluation needs a separately
planned cohort. Model fitting and final test assignment remain pending.
