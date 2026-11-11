# Untouched-participant evaluation draft

Plan v1, 2026-11-11, written **after** the [label-validity decision](label-validity.md).
This draft fixes an analysis to be reviewed, not permission to download, fit or
assign a final test cohort. Its primary target is **participant-session cognitive
state-anxiety change**, not a 30-second stress class. It is conditional on mentor
acceptance of this narrowing and verification of the questionnaire adaptation.
Changes require a reasoned version bump before any new outcome/quality inspection.
No model or comparison may be chosen from the completed pilot accuracies.

## Target, intended use and independent observations

Primary outcome is released cognitive post mean minus cognitive pre mean, in
original score units. Positive means increased reported cognitive anxiety, not a
thresholded stress diagnosis. This is a specified subtraction, not an assumption
about the original article's undefined pre-normalization formula. Secondary
outcomes are separate somatic and self-confidence differences; higher confidence
change means increased confidence. Do not combine dimensions, binarize values,
or choose whichever outcome gives the strongest result.

One row and one prediction per participant-session per outcome/model. The
released dataset contains one session per participant. If further sessions ever
exist, all belong to the same participant partition; use participant-clustered
inference. Three recordings or eighteen windows are measurements within that
session, not eighteen independently observed anxiety outcomes.

The estimand is association between camera response during a known structured
protocol and a post-session self-report change. It is retrospective same-session
estimation, not future stress prediction. Recordings cover only retained clips;
the questionnaire follows the full protocol. This design cannot validate a
passive webcam's momentary-stress output. A webcam deployment claiming that
function needs the additional time-local/behaviour-matched validation in the
label decision document.

## Cohort and lock gates

Keep **s1–s6 and s25 development-only** for every future outcome, regardless of
their historical engineering-pilot roles. Their labels, quality and pipeline
behaviour have been inspected. Their completed LOPO results do not become
independent evidence through a new target or split.

Before any new participant is opened, a designated allocation process must:

1. Verify the form/scoring interpretation and obtain mentor agreement on target,
   population and acceptable error. Establish a participant-based sample-size/
   precision rationale. Seven exposed sessions do not establish adequacy; window
   counts cannot supply it. Do not set N from expected accuracy or pilot winners.
2. Inventory prior exposure and availability without inspecting new video,
   pulse, anxiety values or signal quality. Exclude all previously inspected
   people from the untouched pool. Use consent, identity and structural criteria,
   not outcome, reference agreement, convenient quality or model correctness.
3. Fix acquisition order, participant counts and disjoint development/validation/
   final-evaluation roles in a private manifest. Use seed 20261113 with a recorded
   algorithm and scenario stratification where feasible; scenario metadata can
   be handled by an allocation custodian, not used to optimize response scores.
   Preserve all tasks/derivatives within one role. The protocol's approximate
   60/20/20 allocation remains a planning starting point, subject to the justified
   independent-person counts. Final IDs remain unassigned in this draft.
4. Freeze the manifest hash, feature/schema/camera-policy versions, source and
   dependency hashes, analysis version and model parameters before extraction
   quality or outcomes from those participants are examined. Define structural
   failure reporting and preserve a complete scheduled inventory. A structurally
   eligible session with absent camera features stays in the primary analysis.
5. Verify score completeness/units through a separate label-validation step.
   A session missing the actual outcome is retained in the inventory with an
   unscorable-label reason; never impute y or silently exclude it. Report the
   labeled denominator. Predefine any item/scoring discrepancies as a stop/review
   condition, not an opportunity to invent corrected labels.

These gates are unresolved; **no new participant is assigned here**. If enough
independent participants cannot support the intended precision/roles, report
feasibility only and redesign before collection. Do not borrow final participants
for development and still call them untouched.

## Fixed camera summaries and allowlists

Reuse `pilot-camera-v1` timing, face reacquisition and pulse settings unchanged,
and `window-features-v1` scheduled original intervals. Do not tune track, pulse,
support or ROI policies to the new outcome. Wrist signals and questionnaires
are outcome/reference files only, never webcam model inputs.

For every scalar raw window feature in an allowlist, compute its median over
observed values in each task's six original windows. No observed values means
null. For the session vector retain **T2 median minus T1 median** and **T3 median
minus T1 median**; a missing operand gives null. There is no within-session
imputation before this transform, no interpolation and no new validity threshold.
Keep observed-window counts and operand support separately for reporting. This
is a new, prespecified session summary, not a change to existing raw tables.

All feature families and column orders are the explicit allowlists from
`configs/confound-ablation-v1.json` (canonical SHA-256
`3c80cf92a6b5b2973b03f1002fc92ef621e95eaa5b6b083c9e1a91ca74b55873`),
with its pinned baseline/schema hashes. This locks column membership, not the old
classification target or logistic estimator. For each original column, order transformed columns as speech-minus-rest then
arithmetic-minus-rest. Known task slots are part of the structured protocol,
not identifiers learned as numeric predictors. This transform requires known
rest/active recordings at inference and must not be sold as passive monitoring.

Fixed comparisons for each outcome, reported in full:

- No-change prediction: always zero.
- Training-mean outcome predictor.
- Facial geometric values, camera BPM values, and their concatenation.
- Quality-only and missingness-only controls.
- All six mouth/motion-removal families, with/without BPM, from the frozen
  ablation configuration. No post-pilot winner or ROI selection.

There are 13 prediction arms, including two regression controls replacing the
one classification dummy. Session feature widths are twice the raw allowlist
width (facial 16, BPM 12, fusion 28, quality 20, missingness 34; ablations 10/12/6
and 22/24/18). Empty allowlists are unavailable. Support of a difference requires
at least one observed source window per operand; it does not mean complete
recording coverage. Report both. Availability controls are explicitly labeled;
value arms get no added missingness indicators, but imputation can encode absence.

No participant IDs, file paths, dates/times, sex, numeric task labels, recording
order, assigned condition, pre/post questionnaire values or references enter
predictors. Questionnaire pre values are used only to define y, not as an input;
a pre-score-assisted model would be a separate non-camera-only experiment.

## Fixed fitting and evaluation rules

For this proposed regression target, the classifier is not reused as if it were
a regressor. All non-dummy arms use **Ridge(alpha=10.0, fit_intercept=True,
solver="svd")**, no search, no learned feature selection and no target transform
or prediction clipping. This is a fixed planning choice for regularization,
not a pilot-derived optimum. Confirm software/API compatibility and record exact
versions before eventual execution. There is no stochastic fitting or confidence
calibration in this draft.

Split participants before fitting. Inside every training fold only, drop
all-missing columns, median-impute retained columns, then StandardScaler.
Transform held-out participants with those fitted objects. Keep constants;
if no requested column remains, explicitly fall back to the training-mean
outcome. Validation/test observations never determine a median, scale, dropped
column, feature choice or target transformation. Keep raw derived features.

Use participant-held-out development folds for feasibility; freeze one final fit
on the designated development pool before opening final-evaluation outcomes.
All prespecified arms are evaluated once on that same untouched set, without
selection of a headline winner. Validation is reserved for preregistration
checks; it does not tune this fixed model or supply final-fit statistics. Any
method change prompted by new validation results needs a revised lock before
final evaluation. Existing classification settings remain unchanged for the
separate engineering task benchmark; they do not define this new regression.

Primary metric: equal-participant **MAE** of cognitive-anxiety change. Report
RMSE, mean signed error, and R² (undefined for insufficient/constant outcomes)
with no replacement zero. Compare paired participant absolute errors to both
no-change and training-mean controls and show every predefined model. Report
secondary outcomes separately, without claiming a confirmatory result for the
best dimension. Any formal multiple-outcome hypothesis testing requires a
separate prespecified multiplicity/power plan; none is claimed here.

Primary evaluation retains all structurally eligible sessions with measured y,
including those needing imputation or fallback. Secondary supported-session
results report their denominator and outcome distribution; they cannot replace
the primary population. For each outcome/model, save exactly one keyed prediction
per scheduled labeled session with role, configuration, probability-free point
estimate, truth, support and failure/fallback status. Report unmatched/missing
labels and all extraction failures separately. Never count windows as independent
replications; any interval resamples participants, with small-cohort limitations.

Report distributions, score changes and errors by assigned scenario and support
strata after prediction, where denominators permit. Compare nuisance controls,
coverage by task, and errors on naturally unsupported sessions. Do not stratify
thresholds or exclude people using questionnaire response, group assignment,
pulse agreement or prediction correctness. Camera/wrist checks stay recording-level
while synchronization remains unverified. No wrist feature enters any model.

## What untouched participants would and would not resolve

This plan tests between-person transfer of a session anxiety association under
the same protocol. It does not remove fixed task order, different speaking
content, motion, expectancy, lighting/experimenter effects, or condition-dependent
missingness. A high regression score would still need independent construct
validation and a justified use population. A failed/null association is a useful
outcome, not a reason to replace the target with `test`/`ctrl` and call it stress.

For the original moment-to-moment objective, the next experimental design must
vary psychological demand while matching speech/movement and recording
conditions, obtain repeated time-local validated ratings with known response
lags, include recovery and replication, and validate temporal alignment. New
participants alone cannot provide missing labels or fix task confounding.

The immediate next step is a mentor-reviewed target/scoring/precision decision
and signed-off preregistration. Acquisition, fitting, calibration, rejection
policy learning and final cohort assignment are subsequent separately scoped
steps. This draft does not alter the completed experiments or authorize them.
