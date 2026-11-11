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
6. **Baseline models — blocked on larger pilot review and split gates.** Establish simple reproducible baselines and compare
   modalities using the predefined participant-separated evaluation protocol.
7. **Quality-aware fusion and unreliable-input rejection** — Explore fusion guided
   by quality indicators and reject unreliable input. Tune thresholds using
   training and validation participants only.
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
complete. Next, freeze and construct feature tables with all scheduled rows,
explicit missingness/quality flags, original time axes, policy versions and
participant provenance. Keep camera/wrist combinations at recording level while
synchronization is unverified. Review ambiguity, long-return handling and
condition-dependent availability before complete-case analysis. Pulse validation,
synchronization, live capture, HRV, further cohort acquisition and stress-model
training remain pending; evaluation roles and cohort size still need justification.
