# Locked session-anxiety outcome evaluation

Completed 2026-11-12. This evaluates **ten reserved participants with unconfirmed external exposure history**, not a certified untouched cohort. All comparisons were fixed before their outcomes were opened. The [locked design](untouched-evaluation.md), targets, feature summaries, preprocessing and twelve models remain unchanged. No deployment model is selected.

## Verification and outcome release

The evaluator verified the original complete-lock receipt and its hash manifest, canonical configuration/allocation, model inventory, prediction hash, all 120 participant/model/outcome keys and all 180 scheduled window keys. Frozen-model validation also reproduced the saved predictions before label access. The passing verification receipt was persisted before any questionnaire was copied or parsed. The original lock, prediction/model artifacts and sealed source files remain unchanged; evaluation-only copies were released into a separate ignored output.

All ten canonical participant/metadata chains and questionnaire transport fingerprints matched. Every headerless matrix had the documented 3×2 shape and finite values in the 1–4 mean scale. Rows are cognitive anxiety, somatic anxiety and confidence; columns are pre-session then post-session. This mapping comes from the official README, not inference from numerical values. Both post anxiety outcomes are scorable for all ten people; no missing labels were imputed. Confidence and pre scores were validated separately and do not become predictors or modeled endpoints. Item scoring is not reconstructed. See [released-score interpretation](released-anxiety-targets.md).

One session per person is the independent outcome observation. All 120 saved predictions are scored, retaining unsupported source windows and null features. Errors are computed without refitting, clipping, transformation, changed settings or participant replacement. MAE/RMSE use the released score units; R² uses the outcome mean in the evaluated population as its reference and can be negative. Per-person R² is undefined for one session.

## Primary: post-session cognitive anxiety

All rows have n=10. ΔAE is mean paired absolute error minus the training-mean absolute error on the same people; negative improves on training mean.

| Model | MAE | RMSE | R² | Mean paired ΔAE | Better / worse / tied vs mean |
|---|---:|---:|---:|---:|---|
| Training mean | 0.5571 | 0.7487 | -0.0069 | +0.0000 | 0 / 0 / 10 |
| Facial | 0.5513 | 0.7346 | 0.0308 | -0.0058 | 5 / 5 / 0 |
| BPM | 0.7013 | 0.9279 | -0.5463 | +0.1442 | 5 / 5 / 0 |
| Combined | 0.6879 | 0.8870 | -0.4131 | +0.1308 | 4 / 6 / 0 |
| Quality | 0.6911 | 0.8337 | -0.2485 | +0.1340 | 4 / 6 / 0 |
| Missingness | 1.0407 | 1.9550 | -5.8644 | +0.4836 | 4 / 6 / 0 |

## Secondary: post-session somatic anxiety

All rows have n=10; the same paired-difference definition applies.

| Model | MAE | RMSE | R² | Mean paired ΔAE | Better / worse / tied vs mean |
|---|---:|---:|---:|---:|---|
| Training mean | 0.3192 | 0.4289 | -0.0001 | +0.0000 | 0 / 0 / 10 |
| Facial | 0.4114 | 0.5141 | -0.4370 | +0.0922 | 4 / 6 / 0 |
| BPM | 0.8090 | 1.0315 | -4.7851 | +0.4898 | 2 / 8 / 0 |
| Combined | 0.6793 | 0.8946 | -3.3516 | +0.3601 | 4 / 6 / 0 |
| Quality | 0.4391 | 0.5949 | -0.9246 | +0.1199 | 2 / 8 / 0 |
| Missingness | 0.5627 | 0.8767 | -3.1793 | +0.2435 | 4 / 6 / 0 |

## Interpretation

Facial features have a **0.0058-unit lower cognitive MAE** than training mean (0.5513 versus 0.5571) and a slightly lower RMSE. Five people improve and five worsen. The largest individual improvement exceeds the total net gain across all ten; the pooled advantage is small and depends on the mix of individual gains and losses. It does not show consistent improvement across people. No other model beats training mean on cognitive MAE/RMSE.

No model beats training mean for the secondary somatic outcome on MAE or RMSE. The earlier six-person development result favoring BPM does not carry over to these reserved-participant comparisons. These are descriptive observations, with no significance or superiority claim.

Facial MAE/RMSE is lower than both quality and missingness controls for both outcomes. Cognitive facial errors improve on quality for 7/10 people and on missingness for 6/10; somatic facial improves on each control for 5/10. Combined cognitive MAE is only slightly lower than quality-only MAE, and its RMSE is worse. BPM and combined somatic errors exceed both controls. Improvement over these controls therefore does not establish useful anxiety assessment or an improvement over simple training-mean prediction.

Individual differences matter: one participant accounts for most of the net missingness-control error increase in each outcome. Raw extrapolating predictions are retained without clipping. Private paired-error plots and individual errors expose these cases; they are not excluded or used to tune a model.

## Missing features and secondary support analysis

All ten people remain in every primary comparison. One person has no observed Green left-cheek BPM session summary; frozen training-only imputation is retained. BPM and combined therefore have nine aggregate-complete-input people. Facial, quality and missingness input sets are aggregate-complete for all ten. A non-null session median is not evidence that all 18 source windows or all tasks were supported. All per-column and per-task observed/missing counts remain private in support.json.

The predefined secondary complete-input analysis uses the matched training mean on exactly the same nine people. It does not replace the ten-person primary evaluation:

| Outcome | Model | n | MAE | Matched mean MAE | RMSE | Matched mean RMSE |
|---|---|---:|---:|---:|---:|---:|
| cognitive_post | BPM | 9 | 0.5905 | 0.5344 | 0.7974 | 0.7473 |
| cognitive_post | Combined | 9 | 0.6026 | 0.5344 | 0.7992 | 0.7473 |
| somatic_post | BPM | 9 | 0.6620 | 0.2542 | 0.8228 | 0.3368 |
| somatic_post | Combined | 9 | 0.5192 | 0.2542 | 0.6243 | 0.3368 |

All four secondary comparisons remain worse than their matched means. Secondary R², undefined-metric reasons and complete-support comparisons for all six arms are retained in the detailed metrics.

## Reproduction and private artifacts

The evaluator and tests were committed at `6014106` before outcome release. It lives outside the frozen computation package so introducing evaluation code does not change the predictor-module hash map. Its own source fingerprint, procedure, Git revision, original configuration and pre-release verification are recorded with the evaluation. Existing outputs cannot be overwritten. Reproduction requires a fresh ignored output path and is a replay of an already outcome-exposed evaluation.

```sh
.venv/bin/python scripts/evaluate_locked_anxiety.py --execute \
  --plan data/processed/ubfc-phys/independent-evaluation-plan-v1/acquisition-manifest.json \
  --lock-run data/processed/ubfc-phys/independent-evaluation-v2/complete-cohort-lock-v1 \
  --output data/processed/ubfc-phys/independent-evaluation-v2/outcome-evaluation-v1

.venv/bin/python scripts/evaluate_locked_anxiety.py --validate \
  --output data/processed/ubfc-phys/independent-evaluation-v2/outcome-evaluation-v1
```

The completed output contains evaluation-only questionnaire copies, outcomes.jsonl (one row per session), 120 individual-predictions-errors.jsonl rows, individual-errors.csv, metrics.json, support.json, report.md and three plots: aggregate-errors.png, paired-errors.png and observed-vs-predicted.png. Validation rederives all individual errors, paired differences and metrics from saved locked predictions and released copies without fitting. Original artifacts are checked unchanged. Detailed interpretation is private in outcome-evaluation-review-v1/findings.md.

**150 tests and pip check passed**, plus real execution and separate CLI validation: 120 predictions, twelve model/outcome comparisons and 10/10 scorable people per endpoint. Tests cover blocked release on failed hashes/partial inventory, dimension/order/range mapping, missing-label retention, no clipping or fitting, participant/role alignment, paired signs, undefined R², matched-subset denominators, source preservation and tampered evaluation outputs.

## Scope of the evidence

The locked uncertainty plan specifies **no confidence intervals, significance tests or winner-selection claim**. None is added. Six training sessions are few relative to 6–17 predictors, and ten reserved outcome observations give unstable aggregate errors. External exposure history remains unconfirmed; the authorized evaluation proceeds with that limitation disclosed. These participants are now outcome-exposed and cannot serve as a fresh test cohort for an altered pipeline.

This measures the fixed summaries and frozen regressors under UBFC's recorded protocol. It does not establish ordinary webcam performance, moment-to-moment anxiety/stress, causal measurement, or independence from speech, movement, fixed task order, recording conditions and missingness. Mean post-session questionnaire scores cannot validate window-level or live anxiety. Representative ordinary-camera sessions, behavior/recording controls, an independently planned population and appropriate temporal psychological labels remain necessary for those claims. Independent item-level scoring/psychometric auditing also remains limited.

No deployment model is selected. Calibration, rejection tuning, retraining, further acquisition and a changed evaluation design are outside this completed experiment.
