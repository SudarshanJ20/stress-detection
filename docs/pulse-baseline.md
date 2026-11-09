# Offline camera pulse baseline

Checked 2026-11-09. This command consumes completed local face-quality RGB
traces. It does not reread video, rerun landmarks, train a model, infer stress,
assign dataset splits, acquire participants, estimate HRV, or start live capture.
All participant results, waveforms, reference values and detailed comparisons
stay under ignored `data/processed/`; none are distributed in this repository.

## Verified POS source

Wenjin Wang, Albertus C. den Brinker, Sander Stuijk, and Gerard de Haan,
**Algorithmic Principles of Remote PPG**, IEEE Transactions on Biomedical
Engineering 64(7), 1479–1491, 2017 (online 2016).
[DOI](https://doi.org/10.1109/TBME.2016.2609282),
[official university record](https://research.tue.nl/en/publications/algorithmic-principles-of-remote-ppg/),
[original author manuscript](https://pure.tue.nl/ws/files/31563684/TBME_00467_2016_R1_preprint.pdf).
The university identifies this as a submitted author version; the final
publisher version may differ. Algorithm 1 and its parameter discussion were
inspected directly. The third-party PDF is not committed or redistributed.

Our independent implementation follows its POS core: normalize each RGB channel
by its local temporal mean; project with rows `[0,1,-1]` and `[-2,1,1]`; combine
`S1 + std(S1)/std(S2)*S2`; remove that block's mean and **sum** overlapping blocks.
The paper uses 32 samples at 20 fps (1.6 seconds). Here 1.6 seconds at 40 Hz gives
64 samples, advancing one sample at a time. Population standard deviations have
the same ratio as sample standard deviations for equal block lengths. No
per-sample overlap-count division or core bandpass is added. Degenerate means
or projection variance are rejected rather than stabilized with an invented
pulse. Grid handling, screening and BPM estimation below are project choices,
not a reproduction of the paper's benchmark or an accuracy claim.

## Fixed defaults and measurement definitions

Settings are in `stress_detection.pulse.Settings` and recorded in every run.
They were committed before the local reference comparisons; none were selected
by agreement with this participant's BVP. There is no reference-guided offset,
ROI selection, threshold tuning or best-method selection.

| Parameter | Default / meaning |
| --- | --- |
| Methods | `green` and `pos`, each region independently; no region fusion |
| Regions | `forehead`, `cheek_image_left`, `cheek_image_right` from the saved schema; sides refer to the image |
| Window / stride | 30 seconds / 30 seconds, nonoverlapping, complete intervals only |
| Grid | 40 Hz, origin at the first original presentation timestamp; `origin + k/40` |
| Gap limit | 0.15 seconds between bracketing valid RGB observations; CLI `--max-gap-seconds` |
| Source availability | At least 90% of source frame rows inside the window must have valid finite RGB |
| Grid availability | Every grid point must be exact or supported by two valid observations within the gap limit; no extrapolation |
| POS local interval | 1.6 seconds = 64 samples; same for every region/task |
| Search band | 42–240 BPM inclusive (0.7–4 Hz); a search range, not participant physiology |
| Numerical floor | `1e-8` for usable channel means, POS denominator standard deviation, and detrended signal standard deviation; computational guards, not physiological thresholds |
| Spectral screen | Largest in-band FFT-bin power / total in-band power must be at least 0.10; an uncalibrated engineering heuristic |
| Dependencies | Existing NumPy 2.5.4 and Python 3.12.13; no new packages installed |

Green uses `G/mean(G) - 1` per accepted window. Both methods then use a linear
least-squares detrend, a symmetric Hann taper, and an **unpadded** real FFT.
The largest in-band bin supplies BPM without peak interpolation, harmonic
correction or reference assistance. A 30-second FFT has 2 BPM bin spacing;
medians of bin estimates can fall between bins. There is no separate temporal
bandpass filter: restriction to the search band occurs in spectral estimation.

The reported `spectral_peak_fraction` is the single winning bin's fraction of
in-band power, not SNR, a probability, calibrated confidence, or proof of pulse.
Motion, lighting, harmonics and edge-of-band peaks can pass this screen. A
rejected diffuse spectrum retains its diagnostic but has null BPM. Flat,
nonfinite, zero-channel-mean or degenerate POS signals also produce null BPM.
A completed run can have zero accepted windows. Do not interpret an accepted
estimate as a verified heart rate or a rejected estimate as absence of a pulse.

## Timing, resampling and gaps

The loader requires a completed schema-1 face-quality run, matching status and
summary, successful decode completion, sequential frame rows, exact
`presentation_time_fraction == pts * time_base`, and strictly increasing times.
Missing, duplicate, inconsistent or backward original timing rejects the input;
there is no index/FPS fallback or silent sorting. Invalid region observations
remain missing. Actual finite `mean_rgb` values are used, never overlay pixels.

Source frame indices, integer PTS, rational time bases and exact presentation-time
fractions are copied to the private timing output. A uniform grid is a **derived**
axis; it does not replace those originals. Window bounds are absolute seconds
on that axis, not a silently reset time origin. Duration uses the last original
presentation time plus the reader's reported last-frame duration; if that final
extent is absent the loader refuses to invent it from nominal FPS. Only complete
windows are scheduled; trailing duration is reported. Endpoint frames can support
a nearby grid point across a window boundary within the same gap limit. No
observations cross recordings/tasks.

Linear interpolation is applied separately to each RGB channel only between
valid endpoint observations no more than 0.15 seconds apart. No extrapolation,
long-gap fill, smoothing, brightness enhancement or per-frame normalization is
performed. The 40 Hz grid upsamples the existing approximately 35 Hz recordings;
it adds no physiological information or timing accuracy. The implementation
has no anti-alias filter for other, higher-rate inputs; downsampling those needs
a separately specified filter. Source median sampling rate must exceed twice
the upper search frequency. No claim is made that this detects every aliasing
problem or validates camera acquisition timestamps reconstructed by a demuxer.

`valid_data_fraction` is valid source rows / all source rows in the half-open
window. It is not a time-weighted fraction and cannot reveal absent frame rows
on its own. Independently, `supported_grid_fraction` audits temporal support:
long missing-frame gaps fail even if every surviving source row is valid.
`interpolated_grid_fraction` records supported nonexact grid points. Windows
failing source availability, gap/boundary support or usable-signal checks remain
in the denominator with explicit rejection reasons and null estimates.

## Exact commands

Use the existing environment and **completed** runs; no dataset/model download
or reinstall is needed:

```sh
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m pip check
for task in 1 2 3; do
  python -m stress_detection.pulse \
    --face-run "data/processed/ubfc-phys/face-quality/T${task}" \
    --output "data/processed/ubfc-phys/pulse-baseline/T${task}" \
    --manifest data/processed/ubfc-phys/timestamps/manifest.json \
    --dataset-root data/raw/UBFC-Phys \
    --max-gap-seconds 0.15
done
```

Those output directories now contain the inspected local results. Choose new
output directory names for any repeat; the command refuses overwriting.
`--manifest` and `--dataset-root` must be supplied together for the optional
reference comparison. Omitting both runs camera extraction only. Pairing is
by unique recording ID plus matching source-video hash in the existing
manifest; the BVP path must stay inside the dataset root, have one candidate,
and match its recorded checksum. No questionnaire or task-class label is read
into the pulse estimator. Source recording IDs remain private provenance.

## Private output schema and lifecycle

A new ignored output directory contains:

- `config.json`: schema version, all settings, software versions, algorithm DOI,
  source video and face-frame hashes, landmark-model provenance, optional
  reference hash/path, timing convention, and unverified synchronization.
- `source-timing.json`: original per-frame indices, PTS, rational time bases and
  exact times, origin and reported final-frame extent. No invented sensor times.
- `windows.jsonl`: method, region, window index, original-axis start/end seconds,
  source-valid and grid-support fractions, estimated BPM, peak diagnostic,
  accepted/rejected status and rejection reason. Ordering is fixed by region,
  increasing window index, then method. Every scheduled failure is retained.
- `pulse-traces.jsonl`: method/region/window, original-axis grid start and rate,
  and derived uniform pulse values; failed windows have null waveforms. These
  are processed traces, not untouched sensor samples or verified waveforms.
- `reference.json`, when requested: independent BVP estimates, nominal timing,
  rejection reasons, accepted/total coverage and median. Never publish this file.
- `summary.json`: accepted/total windows, coverage, rejection counts and median
  BPM by method/region, trailing time, and optional recording-level differences.
- `status.json`: atomic `running`, `completed` or `failed`. A crash may leave
  `running`; completion means processing finished, not that estimates are valid.

The command reuses the existing ignored-path enforcement, private JSON writer,
manifest fingerprinting and numeric-signal validator. It reads JSONL sequentially
and retains only compact timestamp/RGB arrays and short derived traces, not
landmarks, images or whole videos. Storage grows with compact trace length;
this is an offline baseline, not a live bounded-buffer implementation.

## Independent BVP comparison and synchronization gate

The matching original CSV must pass the existing one-column, finite numeric
validator. BVP uses the documented **64 Hz** rate from the
[dataset documentation audit](dataset-access.md). Its nominal axis is sample
index / 64, not a measured timestamp or a claim of alignment to video. The BVP
estimator uses its own complete 30-second nonoverlapping intervals and the same
spectral band, detrend, taper and peak screen. No camera estimate enters that
calculation. BVP flatness/motion/diffuse-spectrum failures are retained; wrist
BVP is not automatically clean ground truth. No band or screen was relaxed
when the reference or camera failed locally.

For each method/region, aggregate **accepted camera windows** by their median
BPM; independently take the median of accepted reference windows. Report their
signed difference (camera median minus reference median), alongside both
coverages. This is a comparison of recording-level summaries over potentially
different accepted time subsets. It is **not paired-window error**, MAE, waveform
agreement, beat agreement or physiological accuracy. Either empty accepted set
makes its median and difference null. Task and stress labels do not enter these
calculations.

Synchronization remains unverified. Before any paired analysis, establish:

- Official capture/trigger, retained-segment and sample-zero conventions for
  each stream, including whether AVI timing reflects actual capture timing.
- Independent event/timestamp evidence for video-to-wrist offset, clock-rate
  drift, dropped samples/frames and per-task segment alignment.
- A prespecified synchronization/calibration interval and independent validation
  interval if offset estimation is necessary, with offset/drift sensitivity.
- Reference signal validity and the distinction between wrist pulse arrival
  timing, facial pulse timing and ECG; equal nominal durations alone are not
  alignment evidence.

Do not search for an offset that maximizes whole-recording agreement or trim
streams until they appear to match. The existing
[protocol synchronization gate](research-protocol.md#pulse-reference-synchronization-gate--pending)
continues to apply.

## Verification and remaining limits

Synthetic tests cover a known pulse for green and POS, independent matrix-form
POS calculation, irregular sampling/nonzero origins, short-gap interpolation,
long gaps even at high source-valid fraction, missing-source-frame gaps,
no extrapolation, insufficient data, flat/invalid signals, diffuse spectra,
malformed BVP, completed-run validation, hash/path pairing and overwrite refusal.
All three completed local face-quality runs were processed without regenerating
their RGB traces. Every scheduled window, including rejected windows and empty
reference estimates, remains visible in private outputs. Checksums and timing
were audited; the full test suite and `pip check` passed. Per-recording numeric
results and reference values deliberately stay out of Git.

This single-participant engineering baseline does not establish generalization,
pulse accuracy, reliability, stress measurement or physiological synchronization.
Geometric ROIs are not guaranteed skin masks. Color processing by the source
camera, motion, changing masks, pose, compression, aliasing, harmonic selection,
search-band limits, POS edge overlap weights and uncalibrated rejection can all
bias the result. Later work must validate these assumptions independently.
Leave live capture, HRV, further participant acquisition and stress modeling
for separately scoped milestones.
