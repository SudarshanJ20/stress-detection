# Local webcam pulse diagnostics and reference validation

This procedure does not change `pilot-camera-v1`, `decoded-pts-v1`,
`green-pos-baseline-v1`, pulse thresholds, frozen models or prior experiments.
Diagnostics are exploratory observations, not a new estimator or an accuracy claim.
Questionnaire answers are never inputs to this procedure.

## Explicit retention and deletion

Ordinary assessments remain ephemeral. To make a recording available for a
requested diagnostic investigation, explicitly check **Keep the recording on this
computer until I delete it in Settings** before processing. It is unchecked by
default. Cancellation and failures still remove uploads. Settings deletes that
retained original; no video can be recovered after successful deletion.

A separate offline opt-in creates an identifying diagnostic bundle. From the
repository, substitute the selected recording UUID and a new private directory:

```sh
.venv/bin/python -m app_backend.video_diagnostics \
  --recording data/processed/still-local/recordings/RECORDING-UUID.webm \
  --output data/processed/private-webcam-diagnostic-UNIQUE \
  --confirm-private-diagnostics
```

This copies the selected video, runs the unchanged local worker and retains
native face/pulse outputs, RGB traces, processed signals (including explicitly
labeled rejected diagnostic signals), spectra, identifying face overlays and
video-only provenance. Nothing is uploaded. No questionnaire store is opened.
The destination must be new and Git-ignored. Failed/interrupted collection removes
the newly owned copy, never the original. Existing bundles cannot be overwritten. For a development
file, pass `--source prerecorded` to preserve its actual source label.
This offline bundle is separate from app Settings and survives until explicitly
deleted; remove it with:

```sh
.venv/bin/python -m app_backend.video_diagnostics \
  --delete-bundle data/processed/private-webcam-diagnostic-UNIQUE
```

Delete the retained original separately in Settings. Never commit recordings,
plots, extracted traces or identifying reports. For an already extracted,
consented native run, use `--job-dir DIR --confirm-private-diagnostics` instead.
This writes only a new `diagnostics/` child; existing scientific outputs remain.

## What to inspect

- Decoded PTS and time bases, actual interval distribution, missing/duplicate/
  nonmonotonic timestamps, decoded dimensions, source codec/color tags and final
  frame extent. Compare actual PTS span to the recording interaction's 35 seconds.
- A complete frozen 30-second window, valid and supported-grid fractions and
  interpolation gaps. The 40 Hz analysis grid does not mean a 40 fps camera.
  A high interpolated fraction can arise simply because camera PTS and grid times
  do not coincide; inspect gap lengths rather than calling it missing data.
- Tracking coverage and private first/middle/last/extreme-frame ROI overlays.
  `image_left/right` refer to the unmirrored encoded frame, not anatomical sides.
- Raw region RGB, brightness drift, usable ROI pixels and landmark motion.
  Brightness is observed image intensity, not exposure metadata; auto-exposure,
  white balance and lamp flicker cannot be identified from intensity alone.
- All six spectra, exact decision fractions and competing bins, including edges
  and half/double frequencies. Full-spectrum and in-band plot normalizations
  differ and are labeled. The separate time-frequency view uses 8-second windows
  at their actual timestamp centers (7.5 BPM frequency spacing), not the production
  30-second estimator. The ±2 BPM diagnostic band fractions use full-spectrum
  power; the production gate uses a single bin divided by 42–240 BPM power.
- Compare methods and regions, including rejected channels. Rejected candidate
  frequencies are diagnostic annotations, never supported BPM outputs. Correlation
  and shared peaks cannot establish a cardiac origin, movement causality or
  lighting causality. Exploratory FFT-band correlations do not change extraction.
  A candidate at twice an expected pulse is not evidence that halving it is correct.

The generator checks source SHA-256, frozen settings, every replayed decision and
spectrum against production. Raw ROI means are independently recomputed at sampled
frames. Unavailable measurements remain null. A boundary-missing nuisance trace
is marked unavailable instead of extrapolated to obtain a correlation.

## Camera setup and repeatable next recording

1. Use a stationary camera at eye level. Keep forehead and both cheeks visible.
   Choose steady, diffuse frontal light. Avoid backlighting, changing display
   content and strong reflections. Let camera exposure settle before starting.
2. Enable the camera explicitly. Preview checks show full-frame brightness,
   dark/bright pixel fractions, image change between half-second samples,
   dimensions and the browser-reported frame rate. They include the background;
   they are advisory, not validated face/pulse gates. Unknown values are unavailable.
   Sampling stops during recording to avoid extra capture work. There is no live
   face detection, flicker detector or exposure-control measurement.
3. For this diagnostic run only, explicitly choose recording retention. Obtain
   a simultaneous independent contact pulse measurement. Record the reference
   device/model, its averaging interval/known display latency, setup, browser,
   lighting and approximate capture start/end in a private log. Keep reference
   readings out of questionnaire notes and URLs. A second person can log the
   reference without making the recorded person move or speak.
4. Start the preparation countdown, then remain still, breathe normally and avoid
   typing/talking for all 35 seconds. Stay in the tab. Early stop means incomplete;
   retry rather than treating it as a full recording.
5. **Rough BPM comparison:** record timestamped reference-display readings spanning
   the first decoded 0–30 seconds. Retain every reading and all six camera results,
   including rejections. Report the reference range and available averaging/latency;
   a display value with unknown averaging does not establish the exact 30-second
   mean. Do not select a reference reading or camera channel because it agrees.
6. **Synchronized waveform validation:** obtain exportable contact PPG/ECG samples,
   native timestamps, sampling rates and dropped-sample records. Establish a
   shared synchronization event and clock mapping/offset/drift with uncertainty,
   independently of pulse-wave similarity. Use the same predeclared 30-second
   interval, account for device latency and physiological site delay, and report
   alignment uncertainty. Record both raw waveforms; a displayed BPM or manual
   pulse count alone cannot validate waveform timing or beat intervals. Do not
   shift/warp signals retrospectively to maximize agreement.
7. Repeat stationary trials under documented conditions, with breaks. Predefine
   any later movement/lighting challenges and label them separately. Keep failures
   in the denominator. A few same-person trials are feasibility evidence, not
   population accuracy or clinical validation. Do not infer HRV, anxiety or emotion
   from these BPM comparisons.
8. Generate the private bundle, compare all channels and delete both the bundle
   and retained original when the investigation is complete.

Reference devices also have limitations. Follow their instructions; do not treat
consumer display values as error-free ground truth. See the
[FDA pulse-oximeter overview](https://www.fda.gov/medical-devices/products-and-medical-procedures/pulse-oximeters)
and [MHRA guidance](https://www.gov.uk/guidance/the-use-and-regulation-of-pulse-oximeters-information-for-healthcare-professionals).
Their oxygen-saturation accuracy specifications must not be repurposed as pulse-rate
accuracy claims.

## Encoding checks and methodological boundary

The synthetic browser fixture records known red/green/blue patches using the same
preferred browser VP8/WebM encoder and checks decoded RGB order, dimensions and
PTS with `VideoReader`. It exercises real MediaRecorder encoding, not a physical
camera. It deletes the synthetic file afterward. Run:

```sh
.venv/bin/python -m unittest tests.test_video_diagnostics -v
```

A browser may omit final-frame duration, even when decoded PTS span is present.
The existing frozen contract requires a documented final-frame extent and rejects
that input; diagnostics do not substitute nominal FPS or invent duration.
Supporting conservative PTS-span-only scheduling would require a separately
versioned, reviewed timing policy and dedicated fixtures. No such change is made
here. Likewise harmonic correction, new filtering, motion rejection, cross-region
consensus or different thresholds require a separate documented methodological
proposal and reference validation before product adoption.
