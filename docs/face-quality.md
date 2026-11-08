# Face tracking and basic video measurements

Checked 2026-11-08. This milestone uses an established pretrained landmark model
without training a stress model. Measurements are engineering observations,
not validated quality scores, expression labels, or measured stress. No pulse
extraction, final split assignment, or synchronization verification is performed.

## Tool, model, license and environment

Selected **MediaPipe Tasks Face Landmarker 1.2.2**, CPU delegate, synchronous VIDEO
mode. The [official guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker?tab=Python)
documents the task API. [PyPI](https://pypi.org/project/mediapipe/1.2.2/) provides
an arm64 macOS wheel and lists Python 3.12 support. Local installation, inference,
and tests succeeded on the existing Python **3.12.13 / Apple Silicon** environment;
Python and the environment were not replaced.

The public float16 version-1 model bundle is downloaded from:

<https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task>

Locally computed SHA-256:

```text
64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff
```

The CLI verifies that checksum before inference. This pins the inspected bytes,
not a publisher signature. Provenance is in
[configs/face-landmarker.json](../configs/face-landmarker.json); the asset stays
under ignored `models/mediapipe/`. The package and model cards specify Apache
2.0; [third-party notices](../licenses/README.md) retain attribution and the
unmodified license. No model assets or participant images are distributed here.

The [Face Mesh V2 model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf)
describes a model intended for front-facing monocular imagery, not identity
recognition or life-critical decisions. Pose, partial visibility, lighting,
motion and subgroup/domain differences can affect results. Its estimated depth
is not a calibrated physical distance. Local coverage does not validate model
accuracy or fairness. See also the linked detector/blendshape cards in the notices.

Direct versions are pinned in the `face-quality` extra: PyAV 19.0.2,
MediaPipe 1.2.2, NumPy 2.5.4, and OpenCV-contrib-python 5.0.0.93. All resolved
runtime versions, including required transitive dependencies, are in
[configs/face-quality-requirements.txt](../configs/face-quality-requirements.txt).
MediaPipe requires matplotlib, sounddevice and other packages even though this
milestone does not use audio, plotting, or training. No optional training stack
was added. Installed third-party distribution notices remain intact.

**Observed compatibility limitation:** the OpenCV and PyAV wheels emit duplicate
AVFoundation-class warnings when imported together on this Mac. The smoke run,
three complete file-processing runs and synthetic tests completed without a
related failure. This is not a guarantee for live camera capture; investigate
wheel compatibility or process isolation before implementing that application.
No installed native libraries were removed/renamed. MediaPipe also reports
disabled feedback tensors for this bundle; no feedback/detection score is
fabricated. CPU inference was requested explicitly; GPU acceleration was not
tested.

## Reproducible commands

From the repository root, reuse the existing environment:

```sh
source .venv/bin/activate
python -m pip install -r configs/face-quality-requirements.txt
python -m pip install -e '.[face-quality]'
mkdir -p models/mediapipe
if [ ! -e models/mediapipe/face_landmarker.task ]; then
  curl --fail --location \
    https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task \
    --output models/mediapipe/face_landmarker.task
fi
shasum -a 256 models/mediapipe/face_landmarker.task
python -m unittest discover -s tests -v
python -m pip check
```

Compare the displayed checksum with the pinned value above; do not overwrite an
existing model silently. The CLI will refuse a checksum mismatch. No network
access is needed during processing once the model and packages are present.

First perform an explicitly partial 120-frame smoke run:

```sh
python -m stress_detection.face_quality \
  --input data/raw/UBFC-Phys/s25/vid_s25_T1.avi \
  --output data/processed/ubfc-phys/face-quality/smoke-new \
  --model models/mediapipe/face_landmarker.task \
  --manifest data/processed/ubfc-phys/timestamps/manifest.json \
  --max-frames 120
```

Inspect its summary and overlays locally. `partial` is intentional with the
frame limit; it is not evidence of full-recording completion. The optional
manifest verifies that the input hash identifies exactly one existing recording
and supplies its dataset-relative path. Without a manifest the report records
only the basename and source hash, with no inferred participant/task identity.

After the smoke test passes, process the three existing recordings:

```sh
for task in 1 2 3; do
  python -m stress_detection.face_quality \
    --input "data/raw/UBFC-Phys/s25/vid_s25_T${task}.avi" \
    --output "data/processed/ubfc-phys/face-quality/T${task}-new" \
    --model models/mediapipe/face_landmarker.task \
    --manifest data/processed/ubfc-phys/timestamps/manifest.json
done
```

Always choose new output directories. The model configuration can be passed
explicitly with `--model-config`; the default is `configs/face-landmarker.json`.
No new participants are downloaded by these commands.

## Streaming, timestamps and association

`VideoReader` supplies original decode index, PTS, rational time base and exact
presentation time. One frame and bounded temporal state are retained at a time;
there is no recording-sized frame/landmark array. JSONL is appended per frame.
No source video is resized, recompressed, enhanced or overwritten. Model-internal
resizing/normalization is separate from raw-pixel measurements.

The landmark API requires integer milliseconds. Its input is explicitly
`floor(1000 * (original_time - first_valid_original_time) + 1/2)`, calculated
using `Fraction` arithmetic: nearest millisecond, half-up. The original origin
and all original timestamp fields are preserved separately. Missing, duplicate
or backward original timestamps and rounded-ms collisions are recorded and
skipped; no index/FPS fallback, timestamp bump, sorting or silent repair occurs.
Subsequent valid API calls remain strictly chronological. Timestamp gaps and
spacing diagnostics also remain in the shared reader summary.

Two faces are requested to expose multi-face conditions; output at the capacity
of two means **at least** two may be present, not an exhaustive people count.
The first unambiguous single face starts a geometric track. Later frames must
have one face, bounding-box IoU at least 0.2, center displacement no more than
0.5 previous face-size units, and elapsed time at most 0.5 seconds. These are
provisional association limits, not a composite quality score.

After acquisition, any missing/multiple face, timing fault, malformed landmarks,
or continuity failure permanently invalidates that selected track for the run.
Later detections are counted, but there is **no automatic reacquisition or switch
to a different person**. A deliberate new run/manual review is required. This
conservative policy can discard useful data; geometric continuity cannot prove
biometric identity or detect every unobserved replacement. Do not use these
tracks for identity recognition. Detection coverage and selected-track coverage
are reported separately.

FaceLandmarkerResult exposes landmarks and optional expression/transform outputs,
not per-face detection/tracking confidence scores. Those score fields are null;
the configured 0.5 confidence thresholds are not observed scores. Blendshape and
transformation outputs are disabled. Failed rows contain no invented landmarks.

## Coordinates, masks and measurements

Normalized `(x,y,z)` landmarks are preserved as returned. Image x points right,
y down from the top-left; conversion for geometry is `(x*width,y*height)`.
Coordinates can extend outside the visible image. The model's relative z is
scaled similarly to x, not a depth measurement in metres. Geometry uses the
first 468 points, excluding iris additions where stated; all 478 xyz points are
saved for an accepted frame. Rasterized polygon vertices use nearest integer
(`np.rint`, ties to even), independently of API timestamp rounding.

| Measurement | Definition / units |
| --- | --- |
| Face box / relative size | Extrema of first 468 xy landmarks; raw and image-clipped `(xmin,ymin,xmax,ymax)` in pixels; clipped box area divided by frame area. Not a segmentation-derived physical size. |
| Motion | RMS 2D pixel displacement of corresponding first-468 landmarks divided by mean adjacent `sqrt(box_area)` and **original elapsed seconds**. Units: face sizes/s. Includes rigid motion, expression and model jitter; no stress interpretation. |
| Brightness | Mean OpenCV RGB-to-gray 8-bit luma over the face-oval mask excluding eyes/mouth; rounded approximation to `0.299 R + 0.587 G + 0.114 B`. Range 0–255. |
| Temporal brightness | Signed change in that mean divided by original elapsed seconds; null on first/invalid/discontinuous observations. ROI motion and expression can also change it. |
| Dark fraction | Fraction of valid face-mask pixels with luma **<=20**. |
| Saturated fraction | Fraction with luma **>=235**: a near-white proxy, not proof of sensor or individual-channel clipping. |
| Sharpness proxy | Variance of grayscale four-neighbor Laplacian (`ksize=1`) on a one-pixel-eroded face mask to avoid mask edges. Exposure, texture, scale and noise affect it; not a validated blur score. |
| Availability / timing | Actual detector-result face count, selected-track state, region validity/pixel counts, API timing faults and shared reader timestamp diagnostics. |

No motion or brightness derivative is calculated across a rejected observation.
No good/bad quality label, quality fusion weight or stress prediction is made.

Landmark polygons are explicitly defined in `face_measurements.REGIONS` and saved
in run configuration:

- Forehead: `[10,338,337,336,9,107,108,109]`.
- Image-left cheek: `[50,101,205,187,147,123]`.
- Image-right cheek: `[280,330,425,411,376,352]`.

“Left/right” refer to image coordinates, not anatomical sides. Each mask is
intersected with the landmark face oval, clipped by image rasterization, and
subtracts conservative convex eye/mouth hulls, expanded by a square margin with
radius `max(1, round(0.015*sqrt(clipped_box_area)))` pixels. Degenerate/nonfinite
polygons are rejected. A region needs at least **32 pixels**; otherwise its
pixel count/reason are reported and mean RGB is null. Clipping can reduce counts.

For each valid region, mean RGB is the equally weighted mean of **original
decoded uint8 RGB pixels** under that mask. Grayscale conversion is used only
for quality measurements. There is no color enhancement, temporal smoothing,
per-frame RGB normalization, filtering, or pulse estimation. Landmark/model
preprocessing does not replace the source pixels. These polygons are **not
guaranteed skin masks**: hair, facial hair, occluders and changing pose can
contaminate them. A valid pixel count does not prove suitability for rPPG.

## Private outputs and run status

All outputs are Git-ignored under `data/processed/`. A new run contains:

- `config.json`: input hash/relative path, model URL/checksum/attribution,
  measurement parameters, software/Python versions, CPU architecture, timestamp
  convention and association policy. No personal metadata or questionnaire values.
- `frames.jsonl`: one row per processed original frame; original timing,
  explicit API milliseconds, landmarks/box when accepted, raw region RGB,
  measurements and failure/invalid-region reasons.
- `status.json`: atomic run state (`running`, `partial`, `completed`,
  `completed_with_warnings`, or `failed`). A crashed process can leave `running`;
  do not treat that as completed. Fatal initialization/processing errors create
  a failed summary; cleanup errors also mark failure.
- `summary.json`: completion state, shared timing summary, counts/coverage,
  approximate processing time/throughput and local preview filenames. `completed`
  means the stream reached EOF, **not that every region is valid or skin**;
  `completed_with_warnings` additionally flags selected-track losses.
- A few `overlay_*.png` copies. Tinting/drawing is confined to these previews;
  never use preview pixels as region RGB input.

Per-run automated summaries leave visual review pending by design. The separate
local `visual-review.json` records the manual review actually performed. Never
publish either detailed measurement outputs or participant images in Git.

## Sample verification and limitations

A 120-frame partial smoke run passed, followed by all three complete recordings.
Each processed **6,325 frames**, with one face returned and geometrically tracked
on every frame: no missing/multiple faces, timestamp collisions, track losses or
runtime inference failures. This is detector-reported coverage, not annotated
detection accuracy.

| Recording | Valid forehead | Valid image-left cheek | Valid image-right cheek | Processing time | Approximate throughput |
| --- | --- | --- | --- | --- | --- |
| T1 | 6,325 / 6,325 | 6,325 / 6,325 | 6,325 / 6,325 | 87.0 s | 72.7 frames/s |
| T2 | 6,325 / 6,325 | 6,325 / 6,325 | 6,290 / 6,325 | 88.9 s | 71.1 frames/s |
| T3 | 6,325 / 6,325 | 6,219 / 6,325 | 6,029 / 6,325 | 89.5 s | 70.7 frames/s |

Times cover the streaming decode/inference/measurement/JSONL/preview loop,
excluding model initialization and input hashing; total run time is separately
recorded. These are approximate single-machine engineering observations, not
a general laptop benchmark or GPU test.

Beginning/middle/end overlays for all three recordings, the smoke previews, and
one invalid-cheek example were visually inspected locally. In that example a
far-side cheek collapses during head rotation and is correctly marked invalid
for too few pixels. Sparse inspection does not establish all-frame landmark,
skin, identity or physiological validity. Native-library warnings above remain
a compatibility limitation. Synchronization and all pulse/stress-model work
remain pending. One participant still supports pipeline development only.
