# Independent-participant anxiety evaluation — locked design v2

2026-11-11. This replaces the unexecuted v1 change-score/difference-feature draft.
The change is made **before additional participant outcomes are inspected**: use
the documented released **post-session cognitive-anxiety mean** (primary) and
**post-session somatic-anxiety mean** (secondary), and the summaries actually
used in the completed [feasibility run](session-anxiety.md). The
[direct-score decision](released-anxiety-targets.md) establishes interpretation;
item-level reconstruction is unnecessary. Confidence is not a modeled endpoint.
No categories, accuracy percentage, pre-score input or target transformation.

The design is frozen in
[`independent-anxiety-evaluation-v2.json`](../configs/independent-anxiety-evaluation-v2.json),
canonical SHA-256
`c395c8052d582e83c5f24ad8e9cd75e68fd33d94752c3f8caea1567ba591a8d5`.
Detailed assignments and acquisition files are ignored. The private acquisition
manifest is bound by canonical SHA-256
`7a98c6ecd744d8ce0e93cc91abf972dffed0eda16d35a55242b194c831c6b680`.
Changing membership/settings requires a versioned reason before any unblinding;
never substitute people because their scores, quality or predictions are poor.
No data acquisition, new model fitting or reserved outcome inspection occurred.

## Exposure audit and allocation

Reviewed project receipts, feature selections, pilot/review records, regression
inputs/results and canonical UBFC filenames under `~/Projects` and `~/Downloads`
(dependency/build/Git directories excluded). The older local stress-detect
project's source/docs had no UBFC references; unrelated StudentLife payloads were
not opened. Only the seven known exposed participants had local UBFC originals/
archives. Existing published individual-signal examples were also considered.
Evidence paths and hashes are private in
`data/processed/ubfc-phys/independent-evaluation-plan-v1/exposure-evidence.json`.

| Status | Count | Treatment |
|---|---:|---|
| Existing model-development participants | 6 | s1–s6; only these enter the primary training fit |
| Existing engineering-only development participant | 1 | s25; excluded from primary fit and evaluation |
| Published individual-signal examples reviewed | 3 | Conservative exposure hold; not certified untouched |
| Previously reported filename/identity concerns | 2 | Structural clarification hold, not quality-based exclusions |
| No additional exposure found in the reviewed records | 44 | Candidate pool, **not a guarantee of global non-exposure** |
| Reserved final participants sampled from that pool | 10 | Locked final cohort for this bounded evaluation |
| Remaining candidate participants | 34 | Unassigned, not downloaded or examined |

Individual hold IDs/reasons and final IDs are in the private manifest. The final
ten were drawn by `random.Random(20261113).sample(pool_in_numeric_order, 10)`, then
sorted numerically for sequential acquisition. No scenario, score, video quality
or previous correctness entered selection. Generic mentions of all participants
in dataset listings do not establish data exposure; published participant-specific
signal examples are conservatively held instead. Known filename concerns are
reports needing clarification, not verified dataset corrections.

**External-history gate:** local absence of files/results cannot establish that
no one inspected those participants elsewhere. A question requesting any additional
exposed IDs is pending. Reservations/design are locked, but independence is not
certified until that history is cleared. Newly discovered prior exposure requires
a documented pre-outcome reallocation/re-lock; if discovered after unblinding,
mark the evaluation compromised rather than quietly replacing people. Do not
claim the entire remaining dataset is untouched.

## Practical scope and model lock

This bounded allocation uses six existing training sessions and ten reserved
final sessions, with **no new tuning/validation cohort**, because all comparisons
and parameters are fixed and there is no search, calibration or rejector tuning.
It explicitly replaces v1's approximate 60/20/20 planning split for this study.
A validation partition must be planned separately if later work needs selection.
Never use this final cohort for that purpose.

Fit all **12** target/model combinations once using all six development sessions;
do not ensemble or select the earlier LOPO fold models. Freeze training-table,
code, dependency, preprocessing and model hashes **before** processing reserved
payloads. The final cohort never supplies a median, scale, dropped-column choice,
coefficient, threshold, target choice or ROI choice. After fixed feature extraction,
save/hash **120** unlabeled predictions (ten sessions × six models × two outcomes)
before the custodian releases final questionnaire values for a one-time join.

Keep every model, regardless of the six-person BPM result:

| Model | Fixed inputs | Columns |
|---|---|---:|
| Training mean | Training outcome mean | 0 |
| Facial | Existing mouth/eye/motion geometric proxies | 8 |
| Camera BPM | Green/POS × all three existing regions, separately | 6 |
| Combined | Facial plus camera BPM | 14 |
| Quality | Existing physical-quality allowlist | 10 |
| Missingness | Existing coverage/failure allowlist | 17 |

Exact allowlists are copied without modification from the frozen regression
configuration. Session summaries pool the 18 original scheduled windows:
observed medians for values/physical quality; observed means for coverage/flags;
all-missing stays null. Preserve per-feature/per-task support separately. Do not
use the old draft's task differences. Questionnaire values, participant IDs,
conditions, tasks, paths, timestamps, order and wrist/reference data are not X.

Ridge remains `alpha=10`, `solver=svd`, `fit_intercept=True`. Training-only median
imputation and StandardScaler; drop training-all-missing columns, keep constants,
and use training-mean fallback if none remain. No added missingness indicators in
value models, feature selection, search, clipping, calibration or target scaling.
SVD is deterministic; allocation seed is recorded, not tuned. Policy remains
`pilot-camera-v1` (`c399e9c4…`), feature schema `window-features-v1` (`7a50f53c…`).

## Failures, denominators and reporting

All ten participants, three tasks each and six intended original intervals per
task stay in the scheduled inventory: 30 recordings, 180 intended windows. Keep
actual original PTS/bounds where observable. Do not manufacture timestamps or
frames when decoding fails; report unknown timing/extent explicitly. No bridging
beyond the existing 0.15 s pulse limit or tracker-rule changes. An affected window's
features stay null; aggregate other observed scheduled values with unchanged
rules. No extra frames/windows beyond the retained protocol are introduced.

Retain entire failed recordings/sessions. Camera-empty but outcome-labeled sessions
receive train-fitted imputation/fallback and remain in primary scoring. Identity,
consent, archive safety or unresolved pairing failures are quarantined, counted
and never silently renamed/replaced. A missing/malformed/nonfinite/out-of-range
outcome is unscorable: never impute y or invent a category. Preserve the scheduled
denominator and report scored/unscored counts per outcome. If structural failure
prevents deriving the fixed summary, retain null inputs and the failure reason;
never promote an incomplete receipt. Label validation is separate from camera QC.

Primary metric is equal-participant **cognitive-post MAE**, in released score
units. Report RMSE, pooled R² (undefined for fewer than two or constant outcomes),
individual predictions/errors and paired absolute-error differences versus
training mean for all models. Report somatic separately as secondary. Per-person
R² is undefined with one session. Report complete-input subsets only secondarily,
with denominators and support; partial-window aggregates are not full support.
No confidence intervals, significance or winner-selection claim in this bounded
study. Scenario/coverage strata can be described after prediction, never used to
rebalance the final cohort, tune settings or exclude hard cases.

Six training people remain very few relative to6–17 predictors, and ten test
people give unstable errors/R² and sparse scenario strata. More windows do not
increase independent outcome N. This is a practical independent-person transfer
check, **not a powered confirmatory study or a statistically sufficient final
cohort for the project**. A wider evaluation needs its own precision/population
plan. “Final” here means locked and not used for development in this study.

## Acquisition, blinding and storage

The [official DataPort listing](https://ieee-dataport.org/open-access/ubfc-phys-2)
was fetched as public HTML on2026-11-11. It advertises participant ZIPs and
restricted `sN_zip` folders. The public tree exposes no individual questionnaire
or info links; all folder entries open the login access modal. Thus **separate
small-file delivery is not verified**, not known impossible. No candidate payload
was requested. First check file-level access after login, before full-video ZIP
transfers. The [author page](https://sites.google.com/view/ybenezeth/ubfc-phys)
links the official hosts; do not use third-party mirrors or publish signed URLs.

The exact filenames and selected entry sizes are in the private acquisition
manifest and `next-files.md`. The first access request is only ten `info_sN.txt`
files (identity/session/scenario metadata), without opening scores or changing
allocation. Request the ten `selfReportedAnx_sN.csv` files **only into sealed
custody** if separate delivery is available; defer their content/release until
models and predictions are locked. They are outcomes, not development metadata.
If finer delivery is unavailable, use each listed `sN.zip` as a conditional
fallback; preserve originals and keep questionnaire members sealed/unparsed.

Each full original bundle has11 files: three videos, three BVP, three EDA, info,
and questionnaire. BVP/EDA are structural/reference companions for existing
commands, never predictors; camera/wrist comparisons remain recording-level
while synchronization is unverified. No new individual-file byte sizes or ZIP
extraction sizes are known before authenticated metadata/central-directory checks.

Current free space at freeze: **551.68GiB**, already accounting for resident
archives and preserved runs. New ZIPs advertise **145.99GB** total, about135.96GiB
if decimal; conservatively charge145.99GiB because host units are unspecified.

| Future allocation, archive fallback | GiB |
|---|---:|
| Ten new original ZIPs retained | 145.99 |
| Extracted originals,20 per participant, provisional | 200 |
| Derived outputs,5 per participant, provisional | 50 |
| Sequential active workspace | 40 |
| Free-space reserve | 100 |
| Required additional free before acquisition | **535.99** |

Planning headroom is15.69GiB **beyond** workspace/reserve, or25.72GiB with decimal
ZIP conversion. This is not an actual archive preflight. Recheck free space and
actual ZIP/member sizes before every participant; increase requirements for
retries without deleting prior outputs. Stop if it will not fit. Already downloaded
ZIPs reduce free space and must not be charged a second time as future transfers.
Direct member delivery could avoid ZIP overhead, but no such saving is assumed.
Process one participant at a time; no parallel extraction/face jobs.

## Commands and current execution gate

Exact acquisition entries, preflight/extraction and existing native processing
commands are saved in the private `processing-commands.md`. They use the existing
ZIP safety/CRC extractor, participant-scoped manifest with explicit `test` split,
face, pulse and diagnostics commands. The questionnaire is moved to sealed storage
without parsing before those stages. Do **not** run the sample validator on final
folders: it computes questionnaire statistics. Hash/CRC bytes do not count as
psychological inspection; parsing, printing or viewing outcome values does.

**Implementation gate before any reserved processing:** the current pilot runner
and feature CLI accept engineering roles only, and regression CLI hardcodes six
LOPO participants. Do not relabel final participants as `pilot_development` or
call the LOPO runner a final-evaluation command. A minimal extension of existing
feature/session export and fit/predict entry points must support explicit
train/test roles, scheduled failures and feature-only final processing with
questionnaire access forbidden. Test it using existing development/synthetic data
and hidden-label leakage tests, then freeze its code before acquisition/processing.
No new audit platform or unavailable CLI is invented for this planning step.
The native command recipes are valid building blocks, not a claim that the
end-to-end final evaluation command already exists.

Before label release, verify disjoint roles, fixed setting/policy hashes,
complete120-key prediction inventory, source/output receipts and absence of score
access. All source outcomes/models/reports stay ignored. No training or test
processing occurred during planning. Existing local development tables/models
are reused as provenance; new final fits are deferred to execution.

This evaluates transfer between people **under the recorded UBFC protocol**.
It does not establish ordinary webcam performance, momentary anxiety, causality,
or removal of fixed order, speech/movement, recording-condition or missingness
confounds. Real-world claims need representative sessions, behaviour-matched
controls and time-local labels/alignment for any momentary claim. New people
alone cannot provide missing psychological ground truth.

## Planning validation

The private `planning-validation.json` records successful canonical hash checks,
unchanged targets/allowlists/settings, reproducible allocation, disjoint six/ten
roles, per-participant test assignments, expected120-key inventory, absence of
new archives, current storage projection and preservation of original experiment
inventories. Native CLI argument schemas were checked with `--help`; deferred
shell/Python recipes passed syntax checks without execution. Fourteen existing
manifest/split tests and `pip check` passed. This is planning validation, not a
CRC/decode/feature/model validation of unavailable final data. Detailed next files
are in the private `next-files.md`; no scores or detailed assignments enter Git.
