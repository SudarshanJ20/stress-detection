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
   - **Multi-participant acquisition — pending.** Freeze participant roles and
     staged storage/acquisition decisions using the protocol before requesting
     more participants. The existing participant is development-only, with no
     generalization claim or training/validation/test split possible alone.
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
6. **Baseline models** — Establish simple reproducible baselines and compare
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
Offline pulse processing is complete only as an engineering baseline; pulse
validation, live capture, HRV, further participant acquisition and stress-model
training remain pending.
