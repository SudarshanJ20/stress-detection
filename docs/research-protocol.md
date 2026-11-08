# Provisional research protocol

Version 0.1, 2026-11-08. Design selected **before additional participant
acquisition**. No models have been trained and no performance is predicted.
Changes must be versioned with reasons before final-test evaluation; a protocol
change after examining test outcomes invalidates confirmatory interpretation.

## Question and scope

**Do measured video-quality features reduce selective task-classification error
at matched coverage compared with confidence-only rejection, on unseen
participants under controlled video degradation?**

The intended input is one camera. Facial behaviour and rPPG are two feature
families derived from the **same video**, not independent sensors. Shared
corruption is therefore expected and must be tested. The narrow candidate
contribution is the incremental value of measured video quality beyond
confidence, with subject-independent evaluation and explicit rejection costs.
It is not the invention of face/pulse fusion, quality weighting, or abstention.
See the primary-source [literature comparison](literature-review.md), especially
[CCT-LSTM](https://openaccess.thecvf.com/content/WACV2024/papers/Ziaratnia_Multimodal_Deep_Learning_for_Remote_Stress_Estimation_Using_CCT-LSTM_WACV_2024_paper.pdf),
[QA-Soft](https://doi.org/10.48084/etasr.19489), and
[selective classification](https://proceedings.neurips.cc/paper/7073-selective-classification-for-deep-neural-networks.pdf).
Novelty remains unverified; a negative result is a valid outcome.

## Labels and prediction targets

| Analysis | Negative / positive | Interpretation |
| --- | --- | --- |
| Primary binary contrast A | T1 rest / T2 speech | Experimental task discrimination under a stress-induction protocol |
| Separate binary contrast B | T1 rest / T3 arithmetic | Same interpretation, reported separately |
| Optional later descriptive analysis | `ctrl` / `test` difficulty assignments | Experimental assignment, not measured stress intensity |
| Optional later participant-level outcomes | Pre/post cognitive anxiety, somatic anxiety, self-confidence | Session self-report; not a per-task or per-window stress target |

Both binary contrasts are required and independently fitted/evaluated. Neither
is selected after seeing which performs better. Do not pool T2 and T3 as one
positive class in the primary analysis, relabel difficulty groups as diagnoses,
or create a synthetic continuous stress score. Questionnaire values never enter
the input features or determine window labels. A questionnaire change could
support a separately preregistered participant-level analysis only, with
appropriate score interpretation and enough independent participants.

Contact BVP is a reference for a later pulse-measurement comparison, not ground
truth for psychological stress. EDA is audit/reference information, not a
deployment input. Do not feed wrist signals into a camera-only classifier.

## Confounds and eligibility

Speech, mouth motion, head pose, expression, exposure, and recording order may
reveal the task. Good task recognition cannot distinguish psychological
response from task behaviour on its own. Report this limitation throughout.
Analyze the two difficulty scenarios separately as a descriptive robustness
check when counts allow; never select a cohort using model correctness.

Prespecify eligibility using file availability, consent/access conditions,
identifier consistency, and structural integrity. Log exclusions and reasons
before feature/outcome analysis. Do not exclude windows merely because reference
agreement or classifier accuracy is poor. Keep a common inventory of scheduled
windows across all methods; missing/failed extraction is an abstention reason,
not an invisible deletion. If an entire participant is structurally ineligible,
report that before splitting and retain the exclusion in the private audit.

Required confound controls are a **quality-only classifier**, a simple
motion/pose-only classifier, and per-task/per-scenario coverage reports. Also
compare quality-based selection with a within-condition shuffled-quality control
on development data. A quality predictor that succeeds mostly by discarding
speech windows does not demonstrate better stress measurement. Test-condition
labels can be used for reporting strata after predictions, never for choosing
acceptance thresholds or fusion weights.

## Participant partitions and fitting rules

The existing inspected participant is development-only. No frame, signal window,
or degraded derivative from that participant may enter a future final test.

Before any cohort windowing, create a private frozen participant manifest with
disjoint **training (approximately 60%), validation (20%), final test (20%)**
roles. These are allocation targets, not claims of statistical sufficiency.
Use a fixed recorded seed and participant-level allocation, balance difficulty
assignments where feasible, and report rounding and stratum counts. Do not
choose the easiest, shortest, or best-performing participants for testing. All
tasks, sessions, clean streams, degradations, and overlapping variants belonging
to one participant inherit the same role. Commit code/configuration for the
split algorithm, not participant data or the detailed participant manifest.

Use participant-grouped inner cross-validation on training participants for
model/feature/hyperparameter selection. At most five folds, reduced if group
counts cannot support them; every fold must contain both task classes. Separate
validation participants into prespecified tuning, probability-calibration, and
selection-threshold roles before fitting. Validation tuning can select the
rejector and quality/fusion parameters; calibration and threshold participants
must not train the base classifier or rejector. If those disjoint roles cannot
be populated meaningfully, use grouped cross-validation for an explicitly
**exploratory pilot**, without a final-test performance claim. Do not substitute
random window splits to manufacture more independent cases.

All learned normalization, imputation, feature selection, PCA, model parameters,
quality-to-error mappings, calibration, and rejection thresholds use only the
appropriate training/validation partitions. Refit each learned preprocessing
step inside each relevant fold. Deterministic per-window operations can run
unchanged on held-out input, but no whole-cohort or held-out participant baseline
normalization is allowed. No outcome-dependent test realignment or reference
quality oracle enters features or rejection decisions. Freeze code, settings,
seeds, feature set, calibrators, thresholds, and coverage grid before opening
final test labels. Evaluate that test once; later changes require a new study.

No statistically sufficient participant count is asserted. Independent people,
not window count, determine evidence strength. A small pilot will have unstable
calibration, highly variable held-out performance, sparse subgroups, and wide
or unreliable intervals. Its purpose is feasibility and estimating variability
for a later precision/power plan, not establishing generalization. Do not
declare success based on a convenient cohort size or expected accuracy.

## Windows, features, and comparisons

Provisional primary windowing: nonoverlapping **30-second** intervals on the
original presentation-time axis within each task, with no cross-task windows.
Use only complete intervals, record trailing time, and preserve acquisition
gaps. A development-only 60-second sensitivity analysis may be specified before
test lock. Do not treat overlapping windows as independent observations. Start
with pulse-rate/coarse pulse summaries; no claim of validated short-window HRV,
PRV, LF/HF, or beat-timing accuracy is permitted without separate validation.
Window duration is a design choice here, not an established physiological
minimum. If development checks show it is unsuitable, amend the protocol before
acquisition expansion/test lock.

Candidate measured quality inputs: luminance/clipping, contrast, blur,
face/skin ROI availability, ROI motion/pose, and PTS gaps or irregularity. Record
definitions and units before implementation. Motion may be both behaviour and
nuisance, so identify shared features and run their removal ablation. A camera
pulse-quality estimate may be a secondary quality family; evaluate video-only
quality separately. No reference-BVP-derived quality or ground-truth degradation
severity is available to the deployable selector.

| Method | Features / rule | Purpose |
| --- | --- | --- |
| Facial-only | Prespecified facial behaviour summaries, simple classifier | Behaviour baseline |
| Pulse-only | Camera-derived pulse summaries, same classifier family/budget | Camera physiology baseline |
| Ordinary fusion | Concatenated standardized summaries; fixed equal-probability late fusion as sensitivity | No quality weighting |
| Confidence-only rejection | Ordinary fusion, calibrated maximum class probability; entropy sensitivity | Main selector baseline |
| Quality-only rejection | Same frozen ordinary-fusion predictions, selector from measured quality | Separate information supplied by quality |
| Confidence + quality rejection | Same frozen predictions; small regularized error/ranking model from confidence and quality | **Primary incremental selector comparison** |
| Quality-aware fusion | Quality-conditioned branch weights, bounded/regularized; compare confidence-only and confidence+quality rejection | Separate fusion benefit from selector benefit |
| Controls | Quality-only and motion/pose-only classifiers; seeded random rejection | Audit confounds and trivial coverage effects |

Begin later modeling with the same regularized logistic classifier family and
matched tuning budgets for feature baselines. The selector may be a small
regularized logistic error predictor trained on out-of-participant predictions
from training cross-validation, never on in-sample errors. Tune on validation
tuning participants, fit probability calibration on validation calibration
participants, set operating thresholds on validation threshold participants.
Do not introduce a deep architecture simply to match a published percentage.

## Coverage, estimand, and rejected windows

Coverage is accepted windows / **all eligible scheduled windows**, including
feature failures as forced rejections. Selective risk is misclassified accepted
windows / accepted windows. Zero accepted windows makes risk undefined, not
zero. Use equal participant weight (each window weight is inverse to that
participant's scheduled-window count) for the primary aggregate; also report
ordinary pooled metrics and individual-participant results.

Primary operating point: **80% target coverage**. Prespecified secondary grid:
50%, 60%, 70%, 90%, 95%, 100%. Those are experimental operating points, not safety
thresholds. Compare confidence-only and confidence+quality selectors using the
**same frozen ordinary-fusion predictions** to isolate selection from changed
classifiers. Primary effect is quality-minus-confidence selective 0/1 error at
matched coverage, macro-averaged with equal weight across the 15 prespecified
single-factor degradation settings, separately for each binary contrast;
negative is improvement. Clean input is a separately reported reference.
Report every condition and both contrasts regardless of direction. Treat the two
degraded-input contrasts as co-primary; any confirmatory hypothesis tests must
use Holm adjustment across those two comparisons, with the participant-level
test and its assumptions specified before test lock. Per-severity and other
ablations remain exploratory; do not select the best severity as the headline.

Two analyses must remain distinct:

1. **Retrospective matched coverage:** within each participant and each
   clean/degradation condition, rank windows using selector scores only. At target
   `c`, accept `floor(c * n_p)` windows for participant `p`, where `n_p` is their
   common scheduled-window count. Every method gets the same participant-level
   budget; break ties by a fixed hash of window ID and a recorded seed. This
   makes weighted and unweighted coverage identical across methods. Report the
   realized coverage, which can differ from the nominal target because of small
   integer counts; do not label a rounded 75% point as exactly 80%.
   This may use held-out **scores** and participant IDs, never held-out labels,
   to trace an evaluation curve. It is a participant-balanced retrospective
   estimand; pooled score-ranking is a secondary sensitivity analysis.
   If forced failures make a target unattainable for any method, mark that point
   unavailable for the comparison rather than deleting failures. This is a
   retrospective ranking estimand, not a deployable threshold guarantee.
2. **Fixed operational thresholds:** choose thresholds on validation threshold
   participants only, freeze them, and apply unchanged to clean and degraded
   final test. Report achieved coverage drift and error; do not retune thresholds
   to recover test coverage. Include any hard quality/failure gates in coverage.

Always log rejection counts/fractions and reasons by participant, task, scenario,
degradation, severity, and extraction-failure status. Report class-conditional
coverage and whether particular participants are almost entirely rejected.
Do not silently count an abstained positive as a true negative or claim lower
false alarms solely by withholding positive-class predictions. Quality-aware
fusion is a separate factorial comparison, so improvements cannot be attributed
to rejection alone when both components changed.

## Metrics and uncertainty

Report at full available coverage and each feasible selective operating point:

- Accuracy, macro-F1, positive stress-task recall, and rest false-positive rate
  `FP / (FP + TN)`, with confusion matrices and raw denominators. Here
  “stress-task” names the experimental positive class, not a diagnosis.
- Accepted-only recall/FPR plus **effective positive detection**
  `accepted true positives / all scheduled positives`, rest false alarms per
  scheduled rest window, and rejected-positive/rejected-negative counts.
- Brier score, log loss, reliability plots, and ECE with a prespecified binning
  rule (10 equal-width bins initially); show bin counts and warn when sparse.
  Report calibration before and after selection. Abstentions have no assigned
  probability; report the missing fraction rather than dropping it silently.
- Risk–coverage curves and area over the common attainable coverage interval,
  with the exact interval stated. No area extrapolation across unavailable points.
- Participant-level paired differences and **95% participant-cluster bootstrap
  intervals**, resampling entire people with all their tasks/degradation pairs
  together. Use 2,000 prespecified resamples; this does not create more independent
  people. Keep identical bootstrap draws for method comparisons. Flag intervals
  as unreliable for a tiny cohort; show individual results. No window-wise
  confidence intervals or t-tests treating correlated windows as independent.

The final-test bootstrap is conditional on frozen fitted models. Development
group-fold/seed variability is reported separately as training instability,
not substituted for test uncertainty. Missing class denominators are undefined
and reported explicitly. No expected accuracy or minimum detectable gain is
invented; any later sample-size calculation must use justified assumptions.

## Clean and controlled degradation evaluation

“Clean” means original dataset video, not artifact-free or physiological ground
truth. Generate transformations only as derived copies/streams, never modify
originals. Apply the same transformed video to both facial and pulse branches.
Preserve original time units, PTS, task labels, and paired window identities.

Initial prespecified single-factor families and severity settings:

| Family | Proposed settings | Timing constraint |
| --- | --- | --- |
| Gaussian blur | Sigma 1, 2, 4 pixels at original resolution | Same PTS |
| Spatial loss | Downsample by 0.75, 0.5, 0.25, then restore size for the interface | Same PTS; record interpolation |
| Compression | H.264 CRF 23, 32, 40; freeze encoder/preset/pixel format before testing | Preserve/check PTS after encode |
| Illumination reduction | Multiply intensity by 0.8, 0.5, 0.25 with documented color-space convention | Same PTS |
| Frame loss | Seeded removal of 10%, 25%, 50% of frames | Retain remaining original PTS and explicit gaps; never renumber time |

These are proposed manipulations, not measured quality values or established
real-world severity calibrations. Freeze implementations/seeds on development
data before final testing, and test repeatability on synthetic inputs. Assign
severity independently of labels and participant characteristics. A common
seeded condition schedule prevents class imbalance caused by the generator.
Evaluate every method on every condition and the same scheduled windows.

Primary regime fits base models and selectors on original training streams and
tunes/calibrates them on original validation streams, then tests frozen systems
on original and degraded held-out videos. It is a shift test, with no assumption
that quality learned on original recordings will generalize to every corruption.
A secondary mixed-degradation regime may fit on transformed **training
participants only** and tune/calibrate on transformed validation participants,
using the same training corruption schedule for all competing methods and
separately frozen models.
Do not adapt on test streams or cherry-pick a favorable corruption level.
Combined corruptions are exploratory until separately specified. Synthetic
corruption does not establish robustness to unseen webcams, real speech motion,
lighting geometry, or other datasets. Preserve all failed conditions in reports.

## Pulse-reference synchronization gate — pending

Before pulse-reference agreement claims, verify official capture/trigger and
retained-segment conventions, signal sample-index origin, timestamps/time bases,
recording gaps, and any documented video–wrist offset. Audit independently per
task; matching nominal 180-second durations is insufficient. Keep PTS-based
video time separate from the BVP/EDA nominal sample-index axes. These nominal
axes are assumptions, not measured timestamps. Wrist BVP is not ECG and may
itself be motion-contaminated.

If an offset must be estimated, prespecify a bounded procedure using an
independent synchronization/calibration interval and development participants;
validate it on a separate interval and quantify offset/drift sensitivity. Do not
maximize correlation against the whole test reference or choose windows based
on test agreement. If there is no defensible timing basis, leave waveform/beat
agreement pending. Never silently resample, trim, or align signals to improve
results. Later pulse-rate and waveform comparisons must report their own
alignment assumptions, reference-quality exclusions and coverage, independently
of task classification. None is claimed completed by this protocol.

## CPU cost and memory

Later benchmarks must cover sequential decode, feature extraction, fusion and
selection, both by stage and end to end. Use CPU execution explicitly; report
OS/architecture, Python/library versions, thread counts, original input sizes,
window duration, and stride in the private benchmark output. Separate model-load
time, first-window acquisition delay, processing latency, and steady-state update
latency. Record five warm-up windows and 30 timed window runs (replays allowed
for engineering benchmarking, not independent statistical samples), median/p95
wall time, processing throughput, and real-time factor. Record peak RSS and
steady-state RSS with platform units documented; bound decode queues so memory
does not grow with entire recording length. No GPU acceleration is assumed or
claimed tested. Do not invent laptop performance before measurements.

## Staged participant acquisition and storage — pending

1. **Current stage:** use the existing sample only to implement the manifest,
   timestamp reader, and synchronization audit. Do not train models or download
   additional participants in this task. Keep this participant development-only.
2. **Inventory stage:** after this design is written, inspect official access,
   per-participant archive/member sizes, terms, scenario availability and projected
   storage without obtaining the full cohort. Choose a reproducible acquisition
   order across the available scenario strata; do not select based on observed
   pulse quality or outcomes. Retain missing/unavailable candidates in the audit.
3. **Engineering pilot:** acquire at most two additional participants per batch
   in a separately authorized task, all three tasks each. The batch size is a
   transfer/storage limit, **not a statistically sufficient cohort**. Validate
   each batch before expansion. Pilot-only grouped validation cannot establish
   population accuracy or reliable risk bounds.
4. **Evaluation cohort:** before reserving a final cohort, make a justified
   precision/power and feasibility plan using participant-level pilot variability,
   label support, and storage inventory. Allocate roles using the policy above,
   document deviations, then acquire in batches. If separate validation roles or
   credible final uncertainty cannot be supported, remain exploratory and report
   the limitation instead of promising a participant count.
5. **Storage accounting:** remeasure free bytes before every transfer. Required
   peak space is retained ZIPs + extracted originals + bounded derived data +
   active downloads/extraction overhead + operating-system reserve. Keep a
   provisional 100 GiB free reserve and 40 GiB active-batch workspace, revising
   upward if actual inventory requires it. These are engineering allowances,
   not dataset size estimates. The inspected sample uses about 25.74 GiB for ZIP
   plus extraction, with almost no compression saving; it is not a safe upper
   bound for other participants. Previous free space was about 741.55 GiB;
   do not treat it as current or assume the full dataset fits. Prefer approved
   external storage if projections exceed budget. No automatic ZIP deletion.
6. **Derived storage:** stream degradations where possible and retain compact
   manifests/reports instead of full duplicated videos. Budget disk before any
   saved derivatives. All participant manifests, features, images, signals,
   predictions, and detailed reports stay under ignored data/results locations;
   only synthetic fixtures, algorithms, and nonidentifying summaries enter Git.

## Next small implementation milestone: timestamp reader and dataset manifest

Implement **only** a timestamp-preserving sequential video reader and a private
dataset manifest, using the existing PyAV inspection extra. Do not add facial
models, pulse extraction, model training, or further acquisition in this step.

Acceptance criteria:

- Iterate decoded frames with original integer PTS and rational time base;
  expose normalized relative seconds separately, retaining the original origin.
  Detect missing/nonmonotonic PTS, gaps, and count/duration inconsistencies.
  Never silently substitute `frame_index / nominal_fps` or repair timestamps.
- Manifest records dataset/participant/task IDs, relative source paths, file
  sizes and hashes, validation status, signal counts and documented rates,
  video timing/codec/resolution, split role, and synchronization status.
  Questionnaire scores, personal information, credentials, and absolute machine
  paths are excluded. Keep the real manifest in ignored `data/processed/`.
- Keep signal index/rate-derived nominal time explicitly marked as unverified
  relative timing. No asserted video-to-reference offset until the gate passes.
- Synthetic tests cover variable frame timing, dropped-frame gaps, missing PTS,
  nonmonotonic timestamps, mismatched pairs/IDs, and train/test participant overlap.
  Test that window assignment follows PTS rather than rounded nominal frame rate.
- Run on the existing sample, write private machine-readable results, confirm
  bounded-memory iteration and Git exclusions, and document the command. Commit
  reader/manifest code and synthetic tests in small meaningful changes only.
