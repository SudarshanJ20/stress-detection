# Stress Detection

A research prototype to estimate stress-related patterns from webcam facial
behaviour and camera-derived pulse, with video-quality checks.

## Current status

This repository contains the project scaffold and a minimal development environment. There is no trained model
or validated accuracy yet. Dataset access and research novelty remain unverified.
No predictions or research results are available. This is a research project,
not a diagnostic or clinical tool.

## Planned approach

Audit consented research data, split participants before creating windows, extract
facial, pulse, and video-quality features, and compare baselines with quality-aware
fusion and unreliable-input rejection. Evaluate robustness and laptop performance
before building a live webcam application.

## Layout

- `src/stress_detection/`: implementation code
- `tests/`: automated checks
- `configs/`: shareable configuration without secrets
- `data/raw/` and `data/processed/`: local data only; contents are ignored
- `results/`: local experiment outputs; contents are ignored
- `docs/roadmap.md`: research and implementation phases
- `AGENTS.md`: development and data-handling rules

## Getting started

Use Python 3.12 or newer; the development environment has been verified with
Python 3.12. No datasets or machine-learning dependencies are installed. The
package has no runtime dependencies; setuptools is used to build and install it.

From the repository folder, create the environment once using an existing Python
3.12 installation. With uv available, this reuses an installed interpreter and
does not download another Python:

```sh
uv venv --python 3.12 --no-python-downloads --seed .venv
```

Alternatively, if `python3.12` is on your PATH, use
`python3.12 -m venv .venv`. Do not recreate an existing environment unnecessarily.

Activate the environment, install the project in editable mode, and check it:

```sh
source .venv/bin/activate
python -m pip install -e .
python -m stress_detection.environment
```

The standard-library-only check reports Python, the executable, operating system,
architecture, virtual environment status, and free space on the project volume.
With this editable installation it also works from outside the repository; use
`--project-dir /path/to/project` to check a different directory. It does not test
GPU acceleration or scientific-library compatibility.

Read [the development rules](AGENTS.md) and [the roadmap](docs/roadmap.md) before
making changes. Keep credentials, participant data, and model artifacts out of Git.
