# First exploratory participant-held-out task baseline

`stress_detection.baseline` implements the bounded first classification-only
experiment on saved `window-features-v1` data. Both contrasts are required:
rest versus speech, and separately rest versus arithmetic. The six participants
have already informed pipeline development; leave-one-participant-out (LOPO)
separates fitting, not study development. This is exploratory task classification,
with no independent final-test, clinical stress, or population-accuracy claim.
s25 remains development-only and is excluded from every fold.

The experiment completed locally with all predefined models, held-out rows,
fold models, reports and plots validated. All numerical results, predictions,
participant summaries and trained artifacts remain ignored. The private concise
interpretation is at
`data/processed/ubfc-phys/baseline-review/exploratory-lopo-v1-final/findings.md`;
the immutable generated report and metrics are in the experiment root below.
This does not complete the protocol's confidence-plus-quality rejection study.
Calibration and rejection-policy tuning remain later experiments.

## Frozen design

[`exploratory-lopo-v1.json`](../configs/exploratory-lopo-v1.json) was committed
before fitting. Canonical configuration SHA-256:
`9f83f5a31141a6ceecbc9a0179d3777bb35518ae0f7d2d367fb9e9ff5f2934b6`.
The runner rejects modified/unknown configurations. No hyperparameter search,
learned feature selection, held-out threshold selection or post-result model
selection is implemented.

- Six LOPO folds per contrast: five training participants (60 rows), one
  evaluation participant (12 rows); each participant has six rest and six
  contrast-active rows. All scheduled rows receive predictions.
- Logistic regression: L2 (`l1_ratio=0` in scikit-learn 1.9), C=1, solver lbfgs,
  max_iter=5000, tolerance=1e-8, intercept fitted, no class weights, seed 20261111.
- Fixed decision: active if probability **strictly greater than 0.5**; ties rest.
  Dummy uses the training-class prior, not the held-out label distribution.
- Native pools detected by threadpoolctl are limited to one thread. Record
  detected library/thread details; no claim of a formal CPU benchmark is made.
- Confidence calibration, rejection tuning and uncertainty intervals: none.
  Report all six participant results and descriptive participant-macro means.

The configuration includes explicit column lists, not prefixes or dtype-based
automatic selection:

| Model ID | Inputs | Columns |
|---|---|---:|
| `dummy` | Training-class prior | 0 |
| `facial` | Frozen mouth/eye/motion geometric summaries | 8 |
| `camera_bpm` | All Green/POS × three-region BPM estimates | 6 |
| `facial_camera_bpm` | Concatenation of the two value families | 14 |
| `quality_values` | Physical pixel, face/region-area and brightness-change values | 10 |
| `missingness` | Existing frozen coverage/failure-indicator list | 17 |

Quality values are brightness mean/std, dark/saturated-fraction means,
Laplacian-variance mean, face-area mean, absolute brightness-change median and
three region-area means. This is a predefined subset of the broader feature
schema's video-quality list: coverage fractions, no-frame and failure indicators
are excluded to keep the explicit missingness control separate. Dark/saturated
fractions are measured pixel proportions, not missing-data flags. Brightness
change and face/region geometry may still encode activity and nuisance cues.

IDs, task identifiers, timestamps, paths, recording order, targets, wrist values,
questionnaires and reference diagnostics are forbidden predictors. Index files
supply participant grouping and labels only. The importer does not parse wrist
reference payloads. No method or ROI is selected using reference agreement.

## Fold-local preprocessing and support

For each model/fold, inspect **training X only**. Drop columns with no finite
training observations; never resurrect one because a held-out row contains a
value. Median-impute retained columns from training rows, then fit StandardScaler
on the imputed training matrix. Transform evaluation rows with those fitted
objects. Constant observed columns remain (scaler scale 1); no global column
removal is performed. If no requested training columns remain, log an explicit
training-prior fallback rather than inventing medians. This fallback is tested;
fold artifacts record whether it occurred.

Value models do not receive explicit missing indicators (`add_indicator=False`).
Imputation patterns, feature combinations and other values can nevertheless
carry missingness information. Absence of an indicator column does not remove
condition-dependent missingness confounding.

Each prediction records observed/requested feature counts, missing count, raw
observed fraction, training-empty columns, and underlying facial/BPM observation
fractions, alongside probability, truth, decision, participant/fold and config ID.
The **primary** analysis retains all 72 held-out rows per model/contrast,
including rows requiring imputation. Prediction coverage is distinct from raw
feature support.

The **secondary supported-only** subset requires every requested raw input to be
observed and none to be entirely missing in training. Dummy support is vacuous
(all rows); fully present missingness indicators do not mean the underlying
camera values were present. Report denominator, rest/active counts and participant
coverage. These model-specific subsets differ and cannot replace the common
full-inventory comparison. No support rule depends on a probability or outcome.

## Metrics from saved predictions

Close and reread `predictions.jsonl` before constructing metrics or plots. Report
pooled accuracy, balanced accuracy, binary macro-F1, active-task recall, rest
false-positive rate, confusion matrix `[[TN,FP],[FN,TP]]`, and binary Brier score.
Probabilities are uncalibrated. All metrics, per-participant metrics, and separate
equal-participant means are stored for primary and supported-only analyses.
Pooled macro-F1 and mean participant macro-F1 are distinct nonlinear summaries.

With no rows, metrics are null. Active recall needs true active rows; rest FPR
needs true rest rows. Binary balanced accuracy and macro-F1 require both true
classes; single-class supported strata are explicitly undefined, never silently
zero-filled or averaged as full-cohort results. Participant-macro `mean` is null
if any participant's metric is undefined; `available_mean` is separately labeled
with its contributing participant count. No unsupported zero-risk claim occurs.

Coverage/missingness is reported by participant and true class after prediction.
There are no confidence intervals or significance tests in this bounded run.
Any later intervals must resample whole participants, with the limitations of
six development-informed people stated; windows do not create independent people.

## Dependencies and compatibility

Checked official scikit-learn [installation guidance](https://scikit-learn.org/stable/install.html),
[minimum dependencies](https://scikit-learn.org/stable/min_dependency_table.html),
and [logistic-regression API](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)
before installation. Use `l1_ratio=0` rather than the deprecated `penalty` argument.
Installed binary-wheel metadata requires Python >=3.11 for scikit-learn 1.9.1;
SciPy 1.18.1 requires Python >=3.12 and NumPy >=2.0,<2.8. The existing Python
3.12.13 / NumPy 2.5.4 satisfies these constraints. Binary ARM64 wheels installed,
imports and synthetic fits passed, and `pip check` passed without changing NumPy.

Exact local modeling/plotting pins are in
[`baseline-requirements.txt`](../configs/baseline-requirements.txt); the optional
`baseline` project extra lists direct dependencies. Record Python, NumPy,
scikit-learn, SciPy, joblib, narwhals, threadpoolctl, cloudpickle and Matplotlib
versions, platform, full pip freeze and detected thread pools with each run.
Installed wheel requirements and official-source links are also saved in the
private review. No dataset or model-weight acquisition is part of this command.

```sh
.venv/bin/python -m pip install --only-binary=:all: \
  -r configs/baseline-requirements.txt
.venv/bin/python -m pip check
```

## Exact execution and validation commands

From the repository root:

```sh
.venv/bin/python -m stress_detection.baseline --prepare \
  --feature-run data/processed/ubfc-phys/window-features/pilot-s1-s6-v1-final \
  --output data/processed/ubfc-phys/baselines/exploratory-lopo-v1-final

.venv/bin/python -m stress_detection.baseline --execute \
  --output data/processed/ubfc-phys/baselines/exploratory-lopo-v1-final

.venv/bin/python -m stress_detection.baseline --validate \
  --output data/processed/ubfc-phys/baselines/exploratory-lopo-v1-final
```

The completed root already exists: use `--validate` to check it, and a **fresh**
ignored output root to reproduce the experiment. Preparation verifies saved
feature-table inventories, source/schema/role pairing and all previously recorded
computation-module hashes. Added unrelated module names are permitted, allowing
this experiment to consume the original validated tables without rewriting their
receipts. The older feature command's whole-module-map check remains conservative;
use this experiment's validated importer for these saved inputs. No feature or
pilot output is recomputed or modified.

`--prepare` saves the configuration, allowlists, fold identities/row keys, source
hashes, software, code, pip freeze, Git revision/status and a plan digest. It
performs **no fitting**. `--execute` checks the frozen plan, snapshots and inputs
again before training; it refuses modified settings, changed inputs, or an
already executed root. Failed/running outputs remain incomplete and are preserved.
Recover in a fresh root; never promote an interrupted result based on filenames.

The import-stable preprocessing module makes CLI-created models reloadable from
the Python API; a subprocess-to-import regression test covers this path.
Each run saves 72 fold models and their training-only preprocessing statistics,
training/evaluation participant/row identities, effective/dropped columns,
parameters, warnings and fallback status; `predictions.jsonl` has exactly 864
rows (72 per model × six models × two contrasts). `metrics.json` and `report.md`
contain all models and strata. Each contrast has comparison and confusion plots.
All participant outputs remain in ignored directories.

Validation checks full output hashes before loading our own model artifacts,
verifies every expected prediction key and participant split, recomputes
preprocessing from training rows only, checks frozen estimator parameters,
reproduces probabilities exactly from saved models, and reproduces metrics from
saved predictions. It does not refit classifiers or use held-out data to fit
preprocessing. Tests additionally exercise forbidden predictors, source/plan
changes, missing/duplicate/leaked predictions, all-missing training columns,
constant columns and undefined supported-only metrics.

## Status and next experiment

The final frozen run and both CLI/API validation completed for both contrasts.
The original output is preserved after a custom-class pickle-path portability
fix; predictions and metrics are unchanged in the fresh final run. No analytical
parameter was changed in response to held-out results.
No participant or difficult window was dropped; s25 stayed separate. Numerical
comparisons, support failures and per-participant variation are documented only
in the ignored reports. This is the first exploratory baseline experiment, not
an independent final evaluation or a deployable stress model.

The bounded [confound-ablation study](confound-ablation.md) is now executed and
validated under a separately frozen configuration. It preserves this baseline,
compares mouth/motion removal and uses label/participant-independent added
feature missingness. It does not simulate video degradation or remove natural
missingness confounding. Next, plan an untouched participant evaluation with
frozen comparisons. Confidence calibration, rejection-policy learning, broader
acquisition and final cohort assignment remain later work.
