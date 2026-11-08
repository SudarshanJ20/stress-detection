# Stress Detection

A research prototype to estimate stress-related patterns from webcam facial
behaviour and camera-derived pulse, with video-quality checks.

## Current status

This repository contains the initial project scaffold. There is no trained model
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

Environment and GitHub setup are the first phase. No datasets or machine-learning
dependencies have been downloaded or installed. Runtime requirements and execution
instructions will be documented when implementation begins.

Read [the development rules](AGENTS.md) and [the roadmap](docs/roadmap.md) before
making changes. Keep credentials, participant data, and model artifacts out of Git.
