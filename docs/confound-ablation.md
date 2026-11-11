# Bounded exploratory confound ablation

The mouth/motion-removal and added feature-missingness study is implemented,
executed and validated for both experimental task contrasts. It preserves the
completed baseline, raw feature tables, all original intervals and all six LOPO
folds. s25 remains development-only and never enters this experiment. No final
test cohort is assigned. This is exploratory task classification, not evidence
of psychological stress recognition.

## Frozen design

[`confound-ablation-v1.json`](../configs/confound-ablation-v1.json) was committed
before execution (`490faef`). Canonical SHA-256:
`3c80cf92a6b5b2973b03f1002fc92ef621e95eaa5b6b083c9e1a91ca74b55873`.
The saved baseline configuration is unchanged; its SHA is
`9f83f5a31141a6ceecbc9a0179d3777bb35518ae0f7d2d367fb9e9ff5f2934b6`.
The execution receipt records runner revision `5b0208a`, full computation-module
hashes, dependency versions, original baseline and feature inventories, explicit
allowlists, original row keys, fold identities and configuration digest.

Each contrast has six participant-held-out folds: 60 training rows from five
participants and 12 evaluation rows from the sixth. Every model predicts all 72
scheduled rows per contrast. Training-only median imputation and StandardScaler
are unchanged. Training-all-missing columns are dropped; if none remain, the
baseline's explicit training-prior fallback applies. An empty requested ablation
set instead is **unavailable**, never substituted with dummy. All six actual
ablation sets are nonempty.

Logistic regression remains L2, C=1, lbfgs, l1_ratio=0, max_iter=5000, tol=1e-8,
fit_intercept=true, class_weight=null, random_state=20261111. Active requires
probability strictly greater than 0.5; ties predict rest. No hyperparameter,
feature, participant, mask-level or decision-threshold selection occurs. Native
thread pools are limited to one thread as in the baseline.

| New model ID | Facial inputs retained | Columns | With all six camera BPM columns |
|---|---|---:|---|
| `facial_no_mouth` | Eye mean/std/p10; motion median/p95 | 5 | `facial_no_mouth_plus_bpm` (11) |
| `facial_no_motion` | Mouth mean/std/p95; eye mean/std/p10 | 6 | `facial_no_motion_plus_bpm` (12) |
| `facial_no_mouth_no_motion` | Eye mean/std/p10 | 3 | `facial_no_mouth_no_motion_plus_bpm` (9) |

The exact column names and family definitions are in the frozen configuration.
They refer to geometric proxies defined in [the feature contract](window-features.md).
Green/POS BPM for all three regions remain separate; no ROI or method selection.
The saved dummy, facial, camera BPM, facial+BPM, quality-only and missingness-only
baselines remain in every comparison. No participant IDs, labels, tasks, paths,
times, recording order, wrist signals, questionnaires or reference diagnostics
enter predictors. Grouping/reporting metadata remains separate.

The six new feature sets are fitted once on clean training data in each fold
(72 new models). The 72 original baseline models/preprocessors are hash-verified
and loaded without classifier refitting. All value models omit added missingness
indicators, but training-median combinations can still carry missingness cues.

## Added missingness, not simulated video degradation

One PCG64 realization with seed **20261112** generates an iid uniform score for
each of 108 original windows × 41 unique allowlisted predictors. RNG inputs are
shape and seed only; neither labels nor participants enter generation. At levels
**0%, 10%, 30%, 50%**, an otherwise observed cell becomes null if its score is
below that level. Natural nulls remain null. Thresholding a single score matrix
makes levels nested and gives common row/feature cells identical masks across
models and both contrasts, including their shared rest rows.

Masks apply only to held-out inputs; no model, median or scaler is refitted.
The 0% arm must reproduce saved baseline/new-ablation probabilities exactly.
Eligibility depends on observed data, so realized masked fractions need not match
between classes or participants. Report those rates after generation; do not
balance or redraw masks using labels. This supersedes the earlier roadmap's
suggestion of label-balanced masking for this bounded experiment.

The 41-column universe includes physical quality values and the missingness
control's indicators. Derived indicators are **not recomputed** after masking.
Thus this is unstructured added feature missingness, not a physically consistent
camera/video impairment. It neither removes nor randomizes away the dataset's
existing condition-dependent missingness. One realization, correlated rest rows
across contrasts and nested levels provide no general robustness guarantee.

## Exact commands

From the repository root, using the existing environment:

```sh
.venv/bin/python -m stress_detection.confound_ablation --prepare \
  --baseline-run data/processed/ubfc-phys/baselines/exploratory-lopo-v1-final \
  --output data/processed/ubfc-phys/confound-ablations/confound-ablation-v1

.venv/bin/python -m stress_detection.confound_ablation --execute \
  --output data/processed/ubfc-phys/confound-ablations/confound-ablation-v1

.venv/bin/python -m stress_detection.confound_ablation --validate \
  --output data/processed/ubfc-phys/confound-ablations/confound-ablation-v1

.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m pip check
```

The completed root exists. Use validation there, or choose a fresh ignored root
for reproduction. Preparation does no fitting. Execution refuses overwritten,
changed or incomplete plans; failed artifacts remain visibly incomplete and must
be preserved. No new dependency or download is required.

The compatibility importer verifies every module hash recorded by the old
baseline and feature runs while permitting added module names. It verifies the
old inventories and training-only preprocessing/model predictions; it does not
rewrite or promote incompatible old receipts. The new run additionally freezes
the current complete computation-module map.

## Outputs and checks

All participant results are ignored, including:

- `plan.json`, configuration, allowlists, availability and status receipts;
- 72 new fold models and training-only fit statistics;
- `predictions.jsonl`: 864 clean new-ablation predictions;
- `stress-predictions.jsonl`: 6,912 predictions, exactly 72 per model/contrast/level;
- `mask-scores.npy`, `masks.jsonl`: scores and 432 window/level mask records;
- `clean-comparison.json`, `stress-metrics.json`, `mask-rates.json`;
- `report.md`, two clean comparison plots and two missingness plots;
- `validation.json`, with original baseline and feature preservation checks.

Metrics are derived from reread saved predictions: accuracy, balanced accuracy,
pooled macro-F1, Brier, confusion matrices, active recall, rest FPR, per-participant
results and equal-participant means. Each model/level reports support and missing
counts by class and participant. Primary evaluation always retains every row;
secondary complete-input subsets have explicit rest/active denominators and
undefined single-class/empty metrics. Their differing membership is not a common
comparison cohort. No uncertainty intervals or significance claims are made.

Targeted tests cover shared/nested masks, seed-only generation, natural-null and
zero handling, unchanged inputs, empty-set unavailability, forbidden/modified
allowlists, original fold equality, exactly one clean classifier fit per new
model/fold, clean-arm equality, full prediction inventories, plan/output tampering
and refusal to reuse modified baselines. Existing baseline tests retain the
participant-leakage, training-only preprocessing, all-missing-column and forbidden
predictor checks. CLI and imported-API validation both pass.

## Interpretation and next independent evaluation

The private numerical comparison and concise findings are at
`data/processed/ubfc-phys/confound-ablation-review/confound-ablation-v1/findings.md`.
Removing mouth or motion alone leaves substantial task information in the other
family, particularly for speech. Removing both sharply weakens classification;
the remaining eye-only and eye+BPM inputs do not show a consistent advantage over
quality/missingness controls across contrasts. This does not establish an
independent physiological signal. No model is selected from these results.

Mouth movements directly identify speech; eye/head behaviour, pose, exposure,
ROI geometry and recording conditions/order may also identify task. Removing two
summary families cannot remove all such cues. Arithmetic's pre-existing facial
support failures remain imputed and scored, and can themselves encode condition.
Added missingness can hurt probabilities even when a thresholded accuracy barely
changes or temporarily improves. It is not evidence of robustness to real video
impairments or correction of the original missingness confound.

All six participants informed pipeline development. Next, preregister an untouched
participant evaluation and its roles, sample-size rationale, tasks, feature lists,
models and reporting before inspecting outcomes or signal quality. Lock this
pipeline and all comparisons; fit preprocessing on development participants only,
and report every scheduled row plus support-stratified results and controls.
Where feasible, standardize or counterbalance recording conditions/order and
include task-behaviour controls to separate activity from the intended construct.
Do not choose an ablation winner from this pilot. Further acquisition, calibration,
rejection tuning and final test assignment remain separate milestones.
