# Research roadmap

The repository scaffold and Python development environment are set up. There is
no trained model or validated accuracy; research novelty remains unverified.

1. **Environment and GitHub setup — complete.** Local scaffold, development rules,
   ignore patterns, public GitHub repository, and editable Python environment are
   verified. No machine-learning dependencies are installed.
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
5. **Facial, pulse, and quality feature extraction** — Implement facial behaviour,
   camera-derived pulse, and video-quality features; document assumptions and
   failure conditions. Keep participant features out of Git.
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
private dataset manifest, and split validator. Remaining gates are independent
video/reference synchronization evidence and a feasible staged cohort plan.
Facial models, pulse extraction, further participant acquisition and training
have not begun.
