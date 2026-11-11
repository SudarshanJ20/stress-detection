# Session anxiety: released-score regression completed

Updated 2026-11-11. The released CSV values are **author-computed dimension
scores**, not individual item responses. Their meaning, mean scale and pre/post
order are documented. The earlier audit unnecessarily required item-level
reconstruction details before direct prediction. That gate is corrected in the
[source-backed target decision](released-anxiety-targets.md). The original
no-fit audit and all task-classification experiments are preserved unchanged.

The frozen six-session regression now completed for raw post cognitive anxiety
(primary) and raw post somatic anxiety (secondary), with mean, facial, BPM,
combined, quality and missingness comparisons. It is exploratory feasibility in
six development-informed participants, not independent or live validation.
Numerical results and individual released scores/predictions remain private.

## Released target interpretation

This request proposes **raw post-session cognitive-anxiety mean** as the primary
outcome and **raw post-session somatic-anxiety mean** as a separate secondary
outcome. Confidence is audited separately. This differs from the earlier,
unexecuted v1 anxiety-change draft, now superseded by the
[post-score independent evaluation v2](untouched-evaluation.md).
Pre scores are not predictors and no post-minus-pre or ratio target is constructed.
Task identity and test/ctrl never substitute for an individual's anxiety score.

The official README maps three rows to cognitive anxiety, somatic anxiety and
confidence, and two columns to pre/post. The [original paper](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf)
§2.1 describes 7/7/9 adapted items rated 1–4; §4.3 describes dimension item means.
Higher cognitive/somatic means indicate more anxiety; higher confidence means
more confidence. Administration is before the full sequence and after it, not
after each retained three-minute clip. The [official author page](https://sites.google.com/view/ybenezeth/ubfc-phys)
and [DataPort README](https://ieee-dataport.org/open-access/ubfc-phys-2) corroborate
pre/post-session timing. Source snapshots from the completed [label audit](label-validity.md)
were reused and local questionnaire files reinspected; no new participant acquired.

The released matrices pass 3×2 numeric/range checks and are compatible within
0.00101 with means of the stated item counts. This cannot verify item coding.
The following remain unavailable for **reconstruction/independent scoring audit**,
but are not required to use the documented existing computed scores directly:

- The administered wording/language and exact selected-item mapping.
- Reverse-coded items and confirmation of their recoding before averaging.
- Missing-item handling and denominator rules.
- An authoritative computation specification/code connecting the CSV aggregates
  to this adaptation, or equivalent author clarification.

A generic CSAI-2 scoring key cannot silently replace the dataset-specific form.
Raw items and those instructions were not obtained from the inspected material.
The paper's unspecified pre-normalization formula is **not needed for raw post
scores**. Neither reconstruction nor pre-normalization blocks the completed raw
post-score regression. No verified categorical rule for
this adaptation was found; no low/moderate/high bins, quantiles or thresholds
were invented. Classification and class counts remain unavailable. The absence
of an inspected rule is not proof that none exists elsewhere.

## Closest method: verified versus inaccessible

He, Rabbani, Valero and Ahamed, *Competitive State Anxiety Inventory Assessment
Using Remote Photoplethysmography and Deep Learning*, SSE 2023, pp. 277–284,
[DOI 10.1109/SSE60056.2023.00044](https://doi.org/10.1109/SSE60056.2023.00044).
The [author-hosted abstract](https://masudrabbani.com/publications/conference_articles-17-competitive-state-anxiety-in)
confirms same-person baseline/target videos, deep representations, camera HR/HRV
and support-vector regression on UBFC-Phys. This is a direct anxiety-regression
competitor, not evidence that this project is novel.

Crossref resolves the publisher record to [IEEE article 10234361](https://ieeexplore.ieee.org/document/10234361/).
The official PDF request returned HTTP 418 and the web reader did not retrieve
full text; the author's record exposed no retrieved PDF. Exact label construction
(raw post/change/normalization), score-to-clip pairing, baseline period and how
it enters the model, participant-disjoint splitting, selection/preprocessing fit
scope, exclusions and numerical results are **unverified**. The abstract's
qualitative correlation claim is not an accuracy percentage or a verified error
metric. No performance number from this method is adopted.

Lin He's related [2022 dissertation abstract](https://epublications.marquette.edu/dissertations_mu/1161/)
also describes baseline/target fusion and SVR, but its linked full text was not
retrieved. It is a separate work and cannot establish the 2023 conference paper's
exact protocol or results. No author/mentor contact or access-protection bypass
was performed. Public research-source attempts are saved privately under
`data/processed/ubfc-phys/session-anxiety-sources/v1/`.

## Preserved reusable session audit (historical no-fit checkpoint)

`stress_detection.session_anxiety_audit` has **no fitting API or scoring override**.
The frozen [`session-anxiety-audit-v1.json`](../configs/session-anxiety-audit-v1.json)
was committed before the real audit. Canonical SHA-256:
`2caf3fffe1ace181c24a0e7787c32b5c3e513e512aa3836be30d1878d821aec9`.
It is an audit configuration, not an executed regression configuration. Its
historical `modeling_eligible=false` flag is retained unchanged. The new regression
configuration documents a separate direct-score interpretation rather than
rewriting the audit or pretending its original gate was already resolved.

Use the existing compatible `window-features-v1` tables under unchanged
`pilot-camera-v1`. The importer checks source inventories, recorded computation
hashes, schema, roles and original boundaries; unrelated new modules are allowed.
Original task/ablation files and recorded computation modules remain unchanged.
The audit does not rewrite their receipts. Older commands with strict equality
of the complete module-name map may reject newly added modules; that is distinct
from a mutation of their original outputs.

The explicit private selection lists s1–s6, each `development_only`, and the
corresponding original participant directory. s25 cannot enter it. Shape:

```json
{
  "version": "session-audit-selection-v1",
  "participants": [
    {"id": "s1", "role": "development_only", "directory": "/local/path/s1"}
  ]
}
```

The example entry must be expanded to exactly s1–s6. Selection identity, canonical
filenames and the existing info-file validator prevent ambiguous role/ID pairing.
Do not add scores, tasks or conditions to the selection. The actual six-entry
selection is ignored at the path in the commands below.

One session row pools **all 18 original scheduled windows**, without copying
questionnaire outcomes into windows. Values/physical-quality features use the
median of observed window summaries; coverage/failure indicators use their mean.
All-missing aggregates stay null, observed zeros stay zero. Each scalar needs at
least one observed window, with exact observed/missing counts and per-task support
stored separately. A non-null pooled statistic does not certify full support.
No interpolation, normalization, imputation or feature selection is fitted.

The explicit frozen baseline allowlists retain eight facial proxies, six distinct
Green/POS-region BPM values, their 14-value combination, ten physical-quality
values and seventeen coverage/missingness controls (41 unique columns). No wrist,
EDA, reference diagnostics, scores, IDs, paths, times, task codes, conditions or
recording order enter X. The importer hashes reference files only for integrity;
it does not parse/join their values. These pooled summaries are not a replication
of the competitor's baseline-video or HRV method.

The config records a proposed training-outcome-mean comparator and Ridge(alpha=10,
solver=svd, intercept fitted), training-only imputation/scaling and no search.
Neither was run **by the original audit**. Both are now executed under the new
regression configuration. The fold inventory contains five training sessions and
one held-out session, not 60/12 independent psychological observations. Model widths
8/6/14/10/17 relative to five training people severely limit interpretation.
The fixed L2 model now runs the prespecified feasibility comparisons; neither
regularization nor a raw audit makes them adequately powered.

## Exact commands and outputs

```sh
.venv/bin/python -m stress_detection.session_anxiety_audit \
  --feature-run data/processed/ubfc-phys/window-features/pilot-s1-s6-v1-final \
  --selection data/processed/ubfc-phys/session-anxiety/selection-v1.json \
  --output data/processed/ubfc-phys/session-anxiety/audit-v1

.venv/bin/python -m stress_detection.session_anxiety_audit --validate \
  --output data/processed/ubfc-phys/session-anxiety/audit-v1

.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m pip check
```

The real audit exists; use validation or a fresh ignored output directory.
An existing root cannot be overwritten. Failed receipts remain explicitly failed.
Receipts freeze code/configuration/software/Git revision, selection and input
hashes. Validation rederives summaries and score alignment, verifies every output
hash and all six proposed participant splits, and refuses changed inputs.

Private results: six rows each in `X.jsonl`, `index.jsonl`, `outcomes.jsonl` and
`support.jsonl`, plus `folds.json`, allowlists, configuration, audit/report and
receipt. `outcomes.jsonl` retains individual raw pre/post scores separately for
all dimensions, explicitly marked modeling-ineligible. No prediction/model file
exists. `audit.json` records unavailable metrics and exact blockers.
The concise private findings are
`data/processed/ubfc-phys/session-anxiety/findings-v1.md`.

All **135 tests** and `pip check` passed. Nine targeted tests cover row/column
alignment, shape/range/nonfinite values, identities/roles/s25 exclusion, duplicate
or missing windows, no metadata/outcome predictors, null/zero preservation,
shared session inventory, scoring-gate override, reordered/tampered outcomes,
input changes, incomplete runs and absence of all fitting/predictions. CLI and
imported-API validation passed on the real six-session audit.

## Executed regression and exact commands

The frozen [`session-anxiety-regression-v1.json`](../configs/session-anxiety-regression-v1.json)
canonical SHA-256 is
`e9639dc37673a2ff5122c98858ece38a14284b93fd36f3defb88a03e789b471f`.
Target/configuration decision committed before fitting at `ae00721`; runner
revision `3c0c2fd` is recorded in the run plan. No baseline or source audit was
recomputed or modified. The compatibility importer checks every recorded source
module and all old inventories, while permitting unrelated added module names.

```sh
.venv/bin/python -m stress_detection.session_anxiety_regression --prepare \
  --source-audit data/processed/ubfc-phys/session-anxiety/audit-v1 \
  --output data/processed/ubfc-phys/session-anxiety/regression-v1

.venv/bin/python -m stress_detection.session_anxiety_regression --execute \
  --output data/processed/ubfc-phys/session-anxiety/regression-v1

.venv/bin/python -m stress_detection.session_anxiety_regression --validate \
  --output data/processed/ubfc-phys/session-anxiety/regression-v1
```

The root exists: validate there, or prepare a fresh ignored root to reproduce.
Preparation performs no fitting and snapshots configuration, feature lists,
source hashes, original session/fold identities, software, pip freeze and Git
revision/status. Interrupted/failed runs cannot validate or be overwritten.

All six original session rows are retained, with s25 excluded. Training on five
people, each fold fits only its training medians/scaler and the fixed Ridge
(alpha10, SVD, intercept). Mean predictions use training outcomes only. No search,
clipping, learned feature selection, target transformation or categorical bins.
High dimensionality relative to five training sessions is a major limitation,
not a reason for post-result feature selection.

Validated **72 held-out predictions and 72 fold models**, six predictions per
model/outcome. Validation verifies participant separation, target alignment,
training-only medians/scales, model parameters, training-only Ridge normal
equations, saved-model predictions and saved-result metrics.
No regressor is refitted during validation. MAE/RMSE are score units; pooled R²
is computed across six held-out predictions. Per-person R² is undefined with
one session; constant-outcome R² is also explicitly undefined.

Private output root includes `predictions.jsonl`, `models/`, `metrics.json`,
`report.md`, two error plots, receipts and validation. Report tables retain every
individual released post score and held-out prediction. Detailed interpretation:
`data/processed/ubfc-phys/session-anxiety/regression-review-v1/findings.md`.

BPM-only has lower MAE/RMSE than training-mean prediction for both outcomes in
this pilot. Facial-only and combined inputs do not; quality controls improve
somatic errors but not cognitive errors. Missingness-only does not improve either
pooled comparison. All predefined arms are reported without choosing a winner.
These are descriptive observations, not evidence of real-world anxiety sensing.

All pooled session predictors happen to be observed in this run: no imputation
or training-empty fallback was needed. This does not imply all underlying windows
or tasks were supported. Pooling over available values can still encode activity,
recording conditions and missingness; report original per-task counts. Item-level
psychometric auditing remains unverified, independently of endpoint interpretation.

**140 tests and pip check passed**, plus real CLI/API validation. New tests cover
raw post mapping, forbidden predictors, mean/fallback predictions, training-only
preprocessing, undefined/negative R², leakage, 72-key inventory, source preservation,
changed plans/inputs and tampered artifacts. Original experiment byte inventories
remain unchanged; no participant data or predictions are staged for Git.

## Next independent evaluation

Preregister the endpoint, population, participant count rationale, fixed comparisons
and preprocessing before opening untouched people. The six pilot people and s25
remain development-only; do not choose a model from this small result and claim
an independent final test. Behaviour/recording controls and representative sessions
remain necessary. Momentary anxiety needs time-local psychological labels with
justified response lags/alignment; session scores cannot supply them. New people
alone do not remove task confounding. No acquisition, categorical accuracy,
calibration, rejection tuning or live assessment occurred in this run.

## Final-cohort implementation checkpoint

The [locked independent plan](untouched-evaluation.md) now has
[explicit-role export/inference support](final-cohort-processing.md). Twelve
models were frozen on all six development sessions, without changing any target,
feature or Ridge setting. These are separate final-fit artifacts, not an ensemble
or replacement of the exploratory folds. No reserved outcome was opened and no
real final prediction exists. Exposure history outside reviewed records remains
unconfirmed. Acquisition and blinded final processing are later steps.
