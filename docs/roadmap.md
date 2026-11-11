# Research roadmap

The repository scaffold and Python development environment are set up. There is
no trained stress model or validated stress accuracy; research novelty remains
unverified. A pretrained landmark runtime is used for local measurements only.

1. **Environment and GitHub setup — complete.** Local scaffold, development rules,
   ignore patterns, public GitHub repository, and editable Python environment are
   verified. The optional pretrained landmark runtime is pinned; no stress-model
   training stack has been configured.
2. **Dataset access and sample verification — separate milestones:**
   - **Sample access, integrity, and readability — complete.** One participant's
     three tasks passed safe extraction/CRCs, numeric structure, metadata checks,
     complete video decoding, and nine sparse visual checks. See
     [dataset access](dataset-access.md) for limitations and reproducible commands.
   - **Video/reference synchronization — pending.** No timing alignment is
     established; nominally matching durations are insufficient.
   - **Engineering acquisition and local pilot review — complete for the
     prespecified batches; broader evaluation cohort pending.** The camera audit
     established the common decoded-timing and bounded-reacquisition rules.
     The s3–s6 expansion has been processed in two sequential batches under
     unchanged `pilot-camera-v1`, with archive/output verification, complete
     failure inventories and verified resume. The s1/s2 audit is included only
     after explicit component compatibility checks. s25 remains development-only.
     See the [execution status and next gates](next-pilot-batch.md). This is an
     engineering pilot, with no statistically sufficient final cohort assigned.
3. **Literature verification and research question — focused review and
   provisional protocol written.** [Primary-source comparison](literature-review.md)
   identifies prior camera fusion, quality-aware stress fusion, and abstention.
   [Research protocol](research-protocol.md) defines separate task contrasts,
   participant-separated evaluation, matched-coverage rejection comparisons,
   degradation tests, and storage gates. Novelty, inaccessible full-text details,
   physiological synchronization, and wider construct validity remain unverified.
4. **Data audit and participant-separated splits — infrastructure implemented;
   cohort audit and actual split pending.** The timestamp-preserving RGB reader
   and private manifest builder share the existing inspection code. All three
   sample videos passed timing inspection; original PTS/time bases, signal
   counts/rates, relative paths, hashes, conditions, warnings and unverified
   synchronization are recorded privately. Synthetic tests cover timing faults,
   cleanup, ambiguous pairs and participant/recording/window split leakage.
   The sample remains development-only; no real three-way split is created.
   See [data pipeline commands and semantics](data-pipeline.md). Split future
   data by participant before creating training/testing windows.
5. **Facial/basic quality measurements and offline pulse baseline implemented.**
   The existing reader streams pretrained landmarks, conservative single-face
   association, face geometry/motion, raw brightness/clipping/sharpness proxies,
   and geometric forehead/cheek RGB. All three local recordings were processed
   and sparse overlays inspected. Invalid regions are explicit; no composite
   quality score or stress interpretation is produced. See
   [face-quality commands, definitions and limitations](face-quality.md).
   Green and POS offline pulse methods now consume saved per-region RGB with
   fixed windows, timestamp-aware short-gap resampling, explicit rejections and
   independent recording-level BVP summaries. See [pulse baseline](pulse-baseline.md).
   This does not validate pulse accuracy or alignment. Validated quality/skin
   criteria, synchronization, HRV and live extraction remain pending. Model assets
   and all participant measurements/reference values stay ignored.
6. **Raw feature tables and first exploratory LOPO baseline — complete.**
   `window-features-v1` retains all original intervals, camera features and
   missingness, with identifiers/labels and wrist diagnostics separated from
   predictors. The first frozen six-model task-classification comparison ran
   both contrasts with participant-held-out folds and training-only imputation/
   scaling. Full prediction/model inventories and saved-result metrics validated;
   numerical outcomes stay private and s25 stays development-only. See the
   [feature contract](window-features.md) and [experiment commands](exploratory-baseline.md).
   The frozen [mouth/motion and added-missingness study](confound-ablation.md) is
   also executed and validated. No independent final evaluation, calibration or
   rejection-policy tuning is complete.
7. **Label/construct gate before more data or training — audit complete; review
   pending.** The [label decision](label-validity.md) confirms session pre/post
   anxiety outcomes and experimental task/condition labels, with no momentary
   stress ground truth. Exact adapted form/scoring and Supplemental I/II remain
   unresolved for reconstruction, but direct computed-score targets are usable.
   [Independent evaluation v2](untouched-evaluation.md) now freezes post-cognitive
   primary/post-somatic secondary targets, existing summaries, all six model
   families and training-only preprocessing. Six exposed modeling participants
   remain training-only; ten record-audited candidates are reserved as final,
   with external-history clearance pending. s25 remains engineering-only.
   Metadata-only access must be checked after login. [Explicit final-role export/
   inference](final-cohort-processing.md) and its leakage/compatibility tests are
   now implemented. All 12 fixed models are frozen on s1–s6; no reserved outcome
   or real final prediction was opened/generated. The original pipeline and
   planning artifacts are preserved.
   The conservative archive fallback fits the measured budget provisionally;
   actual archive preflight and independent-person precision remain limitations. The bounded
   [post-session anxiety audit](session-anxiety.md) constructed and validated six
   session rows with separate outcomes and preserved no-fit receipts. The
   [direct-score decision](released-anxiety-targets.md) subsequently corrected the
   reconstruction gate: released computed means can be predicted directly.
   Frozen post-cognitive/post-somatic mean/Ridge LOPO feasibility is now complete,
   with no categories or final-evaluation claim. s1–s6 and s25 remain development-only.
   Independent-population/precision planning, calibration and rejection tuning
   remain separate gates; no new acquisition is part of this experiment.
   Quality-aware rejection remains a later separate engineering experiment.
8. **Evaluation, robustness, and laptop performance** — Report measured metrics,
   uncertainty, failure cases, lighting and motion sensitivity, rejection coverage,
   latency, and resource use. Do not invent results.
9. **Live webcam application** — Integrate the evaluated pipeline with explicit
   camera consent, quality feedback, and rejection behaviour. Document research
   limitations and avoid diagnostic claims.
10. **Research report and reproducibility documentation** — Document verified
    literature, dataset access requirements, split protocol, configurations,
    environment, methods, measured results, and limitations without publishing
    credentials or participant data.

**Completed implementation milestone:** timestamp-preserving video reader,
private dataset manifest, split validator, and pretrained face/basic quality
measurement pipeline, and offline green/POS pulse baseline. Remaining gates
include independent video/reference
synchronization evidence, quality/skin/association validation, native-wheel
compatibility review before live capture, and a feasible staged cohort plan.
Offline pulse processing and the local camera recovery audit are complete as
engineering work. Timing eligibility and bounded reacquisition are versioned,
with ambiguity invalidity, motion resets and the original gap limit covered by
regression tests. s25 compatibility is refreshed separately and original outputs
are preserved. The expanded local engineering pilot and its private review are
complete. The versioned raw window feature tables and both task contrasts are
now constructed, with targeted validation and reproduction checks. They retain
all scheduled rows, source/policy provenance and missingness; reference-only
recording diagnostics remain outside predictors. The first fixed exploratory
LOPO baseline and quality/missingness controls are now complete. Frozen
mouth/motion-removal and label/participant-independent added-feature-missingness
checks are also complete; they do not remove natural missingness confounding or
simulate video degradation. The source-backed label audit is now complete:
current findings cover exploratory task classification and session-score
regression; the psychological outcomes are session anxiety dimensions, not
momentary stress. Next, resolve
external-history clearance before any reserved acquisition for the locked v2
session-outcome plan. Explicit-role support and 12-model freezing are complete;
final data processing and scoring remain unexecuted. New participants alone
do not remove task confounding. Camera/wrist synchronization, pulse validation,
calibrated rejection, live capture, HRV, further acquisition and final stress-model
evaluation remain pending. Six development-informed people
provide exploratory evidence only; final evaluation needs a separately planned
cohort. A bounded ten-person final reservation is now frozen privately; it is
not yet exposure-cleared or evaluated and does not establish cohort sufficiency.
