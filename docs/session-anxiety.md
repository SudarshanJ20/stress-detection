# Session anxiety feasibility: data audit complete, fitting blocked

Checked 2026-11-11. The bounded work completed the reusable data audit; **no anxiety
model was fitted**. The user required scoring resolution before fitting. The
adapted UBFC-Phys scoring remains unresolved in the specific ways listed below,
so there are no held-out predictions, baseline wins, MAE/RMSE/R², or categorical
accuracy to report. Unavailable metrics are null, not zero. All completed task
classification and confound-ablation experiments are preserved.

## Target and scoring gate

This request proposes **raw post-session cognitive-anxiety mean** as the primary
outcome and **raw post-session somatic-anxiety mean** as a separate secondary
outcome. Confidence is audited separately. This differs from the earlier
[anxiety-change draft](untouched-evaluation.md); neither draft has been fitted.
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
Still missing:

- The administered wording/language and exact selected-item mapping.
- Reverse-coded items and confirmation of their recoding before averaging.
- Missing-item handling and denominator rules.
- An authoritative computation specification/code connecting the CSV aggregates
  to this adaptation, or equivalent author clarification.

A generic CSAI-2 scoring key cannot silently replace the dataset-specific form.
Raw items and those instructions were not obtained from the inspected material.
The paper's unspecified pre-normalization formula is **not needed for raw post
scores** and is not the reason fitting stopped. No verified categorical rule for
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

## Reusable session audit

`stress_detection.session_anxiety_audit` has **no fitting API or scoring override**.
The frozen [`session-anxiety-audit-v1.json`](../configs/session-anxiety-audit-v1.json)
was committed before the real audit. Canonical SHA-256:
`2caf3fffe1ace181c24a0e7787c32b5c3e513e512aa3836be30d1878d821aec9`.
It is an audit configuration, not an executed regression configuration.

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
**Neither was run.** The fold inventory contains five training sessions and one
held-out session, not 60/12 independent psychological observations. Model widths
8/6/14/10/17 relative to five training people require dimensionality/feasibility
review before a future executable fit configuration; retaining columns for a raw
audit is not a claim that all comparisons are adequately powered.

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

## Next gate and real-world limits

Obtain and verify the adaptation/scoring specification before fitting. Then freeze
a **new executable** post-outcome experiment with dimension-appropriate sample
size/feature limits and independent-group preprocessing, rather than silently
enabling this audit. Do not choose dimensions or predictors from six outcomes.
The prior untouched-participant change-target plan remains an unexecuted draft
and would need explicit revision if the post-score target is adopted there.

A real-world webcam claim additionally needs untouched participants/sessions,
representative conditions, behavioural/recording controls and prospective use-case
validation. Momentary anxiety requires time-local psychological labels with
justified response lags and alignment; session scores cannot supply them. Wrist
agreement is not psychological ground truth. New participants alone cannot remove
task confounding. No new participants, model training, categorical thresholds,
calibration, rejection tuning or live assessment are part of this checkpoint.
