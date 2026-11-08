# Research roadmap

Only the initial repository scaffold is present. There is no trained model or
validated accuracy; dataset access and research novelty remain unverified.

1. **Environment and GitHub setup** — Establish the local scaffold, development
   rules, ignore patterns, and public GitHub repository. Defer dependency
   installation until implementation requirements are defined.
2. **Dataset access and sample verification** — Verify access, licensing, consent,
   available labels, and representative samples before selecting a dataset.
3. **Literature verification and research question** — Read and verify primary
   literature, establish baselines, and formulate a testable research question.
   Do not claim novelty before verification.
4. **Data audit and participant-separated splits** — Audit labels, missingness,
   consent constraints, and quality. Split by participant before creating training
   and testing windows; prevent participant leakage across all evaluation sets.
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
