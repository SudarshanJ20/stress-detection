# Research roadmap

The repository scaffold and Python development environment are set up. There is
no trained model or validated accuracy; research novelty remains unverified.

1. **Environment and GitHub setup — complete.** Local scaffold, development rules,
   ignore patterns, public GitHub repository, and editable Python environment are
   verified. No machine-learning dependencies are installed.
2. **Dataset access and sample verification — in progress.** UBFC-Phys official
   page, public DataPort metadata, license, and README inspected on 2026-11-08.
   Participant packages are advertised; s25 is the smallest listed at 12.85 GB.
   Login is needed to verify actual delivery and individual-file access; extracted
   sizes remain unknown. No sample acquired or inspected; sample verification is
   pending. See [dataset access](dataset-access.md) for sources, storage estimates,
   protocol/label distinctions, unresolved checks, and the exact manual next step.
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
