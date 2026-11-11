# Direct use of released anxiety scores

Decision v1, 2026-11-11, before regression fitting. The earlier session-audit gate
conflated reconstruction of questionnaire scoring with interpretation of an
already computed score. **The released values can be used directly as continuous
outcomes.** This corrects that gate; original audit/configuration/results remain
unchanged historical artifacts.

The official DataPort README's “Self-reported anxiety scores” section explicitly
describes computed scores and a 3×2 matrix: cognitive anxiety, somatic anxiety,
self-confidence rows; pre-experiment then post-experiment columns. These are
**author-computed dimension scores**, not individual item responses.
[Official dataset documentation](https://ieee-dataport.org/open-access/ubfc-phys-2).
The previously downloaded official DOCX/text and source fingerprints are preserved
privately under `data/processed/ubfc-phys/label-audit/label-audit-v1/`.

The original paper §4.3 says item responses were averaged separately for each
dimension and administration. §2.1 specifies 1–4 item responses and directions:
higher cognitive/somatic values mean more reported anxiety; higher confidence
means more confidence. §§2.2–2.3 and Fig.3 locate pre before T1 and post after the
whole protocol. These establish a 1–4 dimension-mean scale, not a task/window
psychological label. [Original paper](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf),
[IEEE indexed text](https://xplorestaging.ieee.org/document/9346017),
[official author page](https://sites.google.com/view/ybenezeth/ubfc-phys).
The local metadata audit corroborates the six-entry matrix layout/range and
participant pairing. Numeric precision is retained exactly, without rescoring.

| Needed to interpret/predict the existing score | Needed to reconstruct or independently audit its scoring |
|---|---|
| Author-computed versus raw item status; dimension identity; mean scale and direction; pre/post order; participant/session pairing | Exact item wording/mapping/language, reverse coding, missing-item denominators, computation code |

The left-hand information is documented. Missing right-hand details limit an
independent psychometric/scoring audit but do not block direct prediction of the
released endpoint. The original paper's unspecified pre-normalization formula
is irrelevant to a raw-post target: do not apply it or invent a change/ratio.
No target meaning/order field remains ambiguous enough to require an author
question for this bounded run. No message is sent. This does not certify the
adaptation for clinical diagnosis or establish momentary anxiety ground truth.

## Frozen exploratory regression

[`session-anxiety-regression-v1.json`](../configs/session-anxiety-regression-v1.json)
freezes the raw post cognitive-anxiety mean (primary) and raw post somatic-anxiety
mean (secondary). Confidence is not a modeled endpoint. No questionnaire value,
condition assignment, task identity, reference/wrist signal or identifier enters X.

Reuse the already audited six session vectors without changing summaries or
allowlists: observed medians for values/physical quality, observed means for
coverage/missingness controls; all-missing remains null. Each session pools its
18 original intervals. Eight facial, six distinct BPM, 14 combined, ten quality
and seventeen missingness columns are retained exactly as prespecified. Neither
ROI nor a reduced feature set is selected from outcomes. These widths exceed the
five-person training size in some arms; the fixed L2 penalty permits a bounded
feasibility fit but does not provide adequate statistical evidence.

Six leave-one-participant-out folds use s1–s6 only (five training sessions, one
held-out). s25 is excluded. Mean predictor uses each training fold's outcome mean.
Other arms use Ridge(alpha=10, solver=svd, fit_intercept=True), unchanged from the
prior proposal; training-only median imputation/StandardScaler, drop train-empty
columns, training-mean fallback if none remain. No added indicators, target
transform, clipping, calibration, feature selection or hyperparameter search.
All scheduled sessions are scored; no model/participant is selected from results.

Report saved individual held-out predictions and raw targets, MAE/RMSE in original
score units, and R² across six held-out sessions. Per-person R² is undefined with
one observation; pooled R² is undefined if outcomes are constant. No categories
or accuracy percentages. Report raw feature support and paired absolute-error
comparisons to mean. No uncertainty intervals/significance claims from six
exposed development participants. This is same-session outcome estimation,
not prospective prediction, independent final evaluation or live assessment.

## Execution status

Both fixed outcomes completed with72 saved held-out predictions and72 fold
artifacts, with all six sessions retained and s25 excluded. Full reproducible
commands and private result locations are in [session anxiety](session-anxiety.md).
No item reconstruction, categories, model selection or additional acquisition
occurred. The original no-fit audit is preserved as a historical checkpoint.
