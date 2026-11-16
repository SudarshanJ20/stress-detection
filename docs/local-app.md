# Still — Anxiety Screening & Wellbeing

A complete local major-project presentation for “Anxiety Screening and Webcam-Based Physiological Monitoring.” The app supplies a **questionnaire-derived GAD-7 screen** and separately attributed **camera observations**. It does not deploy the anxiety regressors, combine the sources into a score, or claim diagnosis or validated live anxiety assessment. Completed experiments, scientific modules, frozen configurations and model artifacts are preserved.

## Real local video observations — 16 November 2026

The primary **Start assessment** action now opens `/workspace/guided`: official GAD-7 questionnaire → review/edit → camera setup and 35-second capture → video review and consent → background local processing → results. `/workspace/assessment` continues to offer questionnaire-only scoring. `/workspace/camera` uses the same capture, consent, analysis and cleanup component. The separate `/workspace/demo` remains clearly labeled and simulated, with no video upload; its outcomes stay out of genuine history/trends. The earlier demo notes below are historical and describe that separate simulation, not the primary assessment.

Before recording, the setup explains that video processing uses the Python service on this computer. Enable camera requests video only, never audio. The timestamp-based 35-second recorder now retains capture chunks only for the real flow; the simulation still discards them. Completed real capture creates a temporary browser Blob and replay URL for review. Nothing is uploaded until **I consent to processing this video locally on this computer** is checked and **Analyze on this computer** is selected. The API also requires the consent flag. Choosing a prerecorded input is explicit and preserves a `prerecorded` source in the interface and export.

The native worker reuses `VideoReader`, the original landmark tracker and `features.summarize_frames`, Green/POS extraction, fixed `pilot-camera-v1` and frozen pulse screens. No scientific module, fitted model, research configuration, dataset source or evaluation artifact was changed. Decoding inspects actual PTS and final-frame extent. Missing, duplicate or nonmonotonic timestamps and undocumented final-frame duration are not repaired with nominal FPS. Half-open feature windows use exact source fractions relative to the first frame; complete 30-second windows only are summarized. A 35-second capture provides boundary support without changing any threshold. Short input produces explicit unavailability; invalid encoding/timing produces an actionable failure.

Real stages are **Receiving video → Waiting for local processing → Decoding video and timestamps → Tracking facial landmarks → Extracting geometric features → Screening camera pulse → Preparing results**. They follow actual work in isolated processes, supervised by the existing single-worker executor. There is no illustrative processing delay or fixed percentage in this flow. Client operations are guarded against duplicate clicks, and cancellation is keyed before the job-creation request. Server cancellation tombstones prevent late requests from resurrecting cancelled jobs.

**Anxiety screening — questionnaire** displays the actual 0–21 GAD-7 sum, published category and last-two-weeks timeframe, with the brief screening-not-diagnosis explanation. **Video observations — webcam** displays:

- Retained face-tracking coverage as a fraction of decoded frames, with no-face and multiple-face counts.
- Mouth and eye opening ratios (projected vertical opening / local corner width; dimensionless). Both eyes are required. Frame means, population standard deviations and quantiles are preserved in the detailed/exported summaries.
- Facial landmark motion (468-point projected RMS displacement, normalized by mean face size and original elapsed seconds). Units are face sizes per second. It combines facial movement and expression; it is not a head-pose or blink-event measurement.
- Camera-derived BPM separately for Green/POS and forehead/image-left cheek/image-right cheek, with rejected values null, readable reasons and search-band-edge flags.
- Actual decoded duration, timestamp span/final-frame extent, codec, decoded-frame count and timing flags.

Each facial statistic requires at least two usable samples and 90% support under the original rules. Motion does not cross clipped faces, segment breaks or gaps over 0.15 seconds. Across multiple supported windows, the reported aggregate is the median of each window statistic, not a whole-video frame-weighted average. Camera BPM is not converted to HRV, stress, anxiety or emotion. JSON reports retain the same values, units, sources, quality flags and per-window support information as the interface; simulation fields have no result in genuine reports.

Browser replay URLs and video references are released after transfer, cancellation or failure. On the server, temporary upload, landmarks/RGB, overlays, pulse intermediates and result files are removed **before** a completed result is returned. Failure never retains a recording, even when retention was selected. Only explicit **Keep the recording on this computer until I delete it in Settings** retains the source upload after successful processing. Those files can be deleted through Settings or their explicitly saved history entry, including after server restart. Browser history is still a separate opt-in and omits raw questionnaire answers. Results are not automatically saved. If a connection is interrupted, cancellation/deletion may need a retry; the existing 30-minute expiry/startup cleanup remains the fallback. Selected original videos and user-downloaded reports are not deleted by the app.

Validation for this update: **162 Python tests passed**, including consent enforcement, cancellation tombstones, worker cleanup/retention and injected deletion failures with retry. The **33-check Playwright suite passed**; the added completed-response cancellation regression and all **eight real-video checks** passed in targeted reruns after the final fixes. TypeScript, production Turbopack build and `pip check` passed. Browser checks cover responsive layouts at 390/768/1440px, keyboard/focus/reduced motion, automated WCAG A/AA/2.1-AA scans, source attribution and JSON/print consistency. The final source was reviewed and runtime/media/model files remain ignored.

A consented development MP4 decoded to approximately 35.32 seconds and supplied one complete analysis interval. It produced supported facial summaries and five supported method/region pulse readings; the remaining Green/forehead reading was rejected for a diffuse spectrum and displayed as unavailable. This is a functionality check, not pulse-accuracy validation. A clearly labeled synthetic browser camera exercised real MediaRecorder WebM capture for 35 seconds, explicit consent, native Python processing and no-face unavailability; all unsupported facial/pulse values remained null. Additional native checks cover invalid encoding, short MP4 input with no complete interval, successful temporary-file deletion, explicit retention followed by history deletion, cancellation during processing, duplicate clicks and revoked browser replay URLs. A delayed cleanup response cannot publish a result after Cancel.

Physical webcam permission prompts, LED/track shutdown, real device disconnection and lighting/pose conditions remain manual checks. Safari/Firefox codec behavior and the native OS print dialog are still pending. Existing Python AVFoundation/resource/test-client warnings remain nonfatal; frozen scientific dependencies were not changed to suppress them.

The user-facing home, assessment, about, results, navigation and privacy copy now describe this real workflow. Research evidence remains in the repository and outside public navigation. The startup commands below remain valid; reuse healthy loopback servers instead of launching duplicates. No public deployment is involved.

## Guided demonstration update — 15 November 2026

The public app now leads with **Start assessment** (`/workspace/demo`). Its connected flow is questionnaire → review/edit → camera setup → optional 3-second preparation → 35-second recording → demo transition → results. **Demo mode — simulated result** remains visible on each demo screen and its JSON/print report. The fixed **62% Illustrative score / Moderate — example** is identical for everyone, never calculated from video or answers, and never presented as a measurement, probability, confidence or accuracy. The actual GAD-7 score remains separate and covers the last two weeks. Pulse, face activity and signal quality explicitly show unavailable in the demo.

**Questionnaire only** (`/workspace/assessment`) retains the official wording, choices, timeframe, 0–21 scoring and category boundaries. The shared questionnaire component preserves answers across internal navigation and supports review/edit. Closing/reloading warns about losing ephemeral progress. Starting a new demo and confirmed cancellation clear demo state. The demo and genuine assessment use separate memory state; an explicit questionnaire-only fallback transfers just the genuine questionnaire answers/score, never an illustrative outcome.

Camera access occurs only after **Enable camera**. No microphone is requested. Capture chunks are discarded immediately without creating replay object URLs, files, backend jobs or uploads. Demo sessions cannot be saved into genuine history; both storage reads/writes and trend calculation exclude `mode: demo`. Downloads require an explicit action and include the simulation label and separately attributed sources. The existing opt-in browser-history deletion and local backend recording deletion remain available outside the demo.

Recording uses a monotonic `performance.now()` deadline, never a timer-callback count. Start/permission operations are guarded against duplicate clicks. Early Stop, lost hardware, recording failure or background-tab interruption produce incomplete/retry states. Tracks and timers are released during completion, cancel, back, pagehide and layout cleanup on navigation; late permission responses are stopped immediately. A browser callback delayed by 500ms or more beyond the target is rejected rather than called a completed 35-second capture. Browser scheduling and encoder boundaries do not guarantee a frame-exact 35.000-second file; the report records actual elapsed capture time. No recording file is retained in this demonstration.

The **1.8-second demo transition** is illustrative only; it never claims pulse extraction or inference. Existing research models are not invoked. The optional genuine Camera session still requires an explicit **Analyze on this computer** action before transfer to the local Python service and remains separate from this demo.

The public Research route and navigation links have been removed. Its original source is preserved verbatim in `docs/archive/research-page.tsx`; the source data remains in `web/lib/research.json`. Research documents, data, frozen configurations, models, predictions and evaluation results have not been changed. The historical implementation/validation notes below are retained as evidence; their references to public Research navigation describe the earlier app.

Startup commands below are unchanged. Do not start another server if these loopback instances are healthy. No public deployment is involved.

Validation for this update: 157 Python tests passed and `pip check` reported no broken requirements. TypeScript and the production Turbopack build passed. All 26 Playwright checks were exercised successfully across the existing 11 checks and 15 demo checks, with targeted reruns after correcting test-selector/fixture issues. Coverage includes all 22 questionnaire totals, incomplete responses, review/edit/resume, explicit permission, denial/missing/busy/unsupported cameras, real MediaRecorder with a clearly labeled synthetic camera, preparation, the 35-second deadline, early stop, retry/cancel/background interruption, delayed permission resolution, duplicate guards, cleanup, export/print attribution, zero demo uploads and exclusion from genuine storage/trends. Browser checks cover 390/768/1440px layouts, keyboard/focus/reduced motion and automated WCAG A/AA/2.1-AA scans. Results screenshots were inspected at mobile and desktop sizes. Homepage and both direct/proxied backend health endpoints returned successfully with the existing loopback servers.

Physical webcam permission/LED/stop behavior, actual camera-disconnection behavior, Safari/Firefox codec behavior and the OS print dialog remain manual checks. Synthetic browser capture does not validate those hardware/browser combinations. The Python suite emits existing PyAV/OpenCV duplicate AVFoundation class warnings, resource warnings and a Starlette test-client deprecation warning; it still completes successfully. Scientific code and pinned dependencies were not changed to suppress these warnings.


## Architecture and compatibility

There was no existing application stack. The implementation adds `web/` (Next.js 16.4.6 App Router, React 19.2.7, TypeScript, Tailwind 4.3.5) and a separate `app_backend/` FastAPI service, leaving the frozen `src/stress_detection/` computation package unchanged. Node 24.15.0 satisfies Next's >=20.9 requirement. `npm ci` uses `web/package-lock.json`; the existing Python environment is extended using `configs/web-requirements.txt`, without upgrading the pinned scientific packages.

The installed Next.js guides were inspected. Development and production builds explicitly use Turbopack; Next telemetry is disabled in the package scripts. Public content is prerendered. Interactive clients are limited to navigation, preview and workspace state; camera controls and trend charts are lazy-loaded. Motion for React handles restrained entrances; GSAP/ScrollTrigger is lazy-loaded only for the landing three-step sequence, with cleanup and reduced-motion guards. Scrolling stays native throughout; Lenis was not needed. Native controls and dialog semantics avoid an unnecessary component framework. Design references, photo/font sources and permissions are in [web/ASSETS.md](../web/ASSETS.md).

FastAPI serves only loopback. A single-worker executor orchestrates isolated child processes; expensive decoding/extraction is outside the HTTP request handler and browser UI thread. Jobs report actual stages, not arbitrary percentages. The service uses the existing `face_quality`, `pulse`, `features.summarize_frames` and spectral-edge diagnostics under unchanged `pilot-camera-v1`. Processing never opens questionnaire or research outcome files and never calls an anxiety estimator.

The frozen session-regression contract pools **18 original windows across three UBFC tasks**. This app does not pretend a short webcam clip supplies that contract. Instead, a 35-second capture target allows a complete **30-second measurement interval** plus boundary support. Short recordings, unreadable or unsupported timing, absent/multiple faces, gaps and rejected spectra produce explicit unavailability or a useful failure. No interpolation beyond the existing gap limit or invented values is introduced. Facial ratios/motion remain geometric proxies; pulse screening is not validated accuracy.

## Start from this repository

Use the existing Python 3.12 environment, local landmark model and pipeline dependencies. The verified model file is `models/mediapipe/face_landmarker.task`; it remains ignored. If absent, follow [face-quality provisioning](face-quality.md), separately from participant data acquisition. The app does not download it automatically. On a fresh environment, install the existing `face-quality` and `baseline` project extras before the web-service requirements. Do not recreate or replace an established research environment unnecessarily.

Terminal 1, from the project root:

```sh
cd ~/Projects/stress-detection
.venv/bin/python -m pip install -r configs/web-requirements.txt
.venv/bin/python -m uvicorn app_backend.main:app \
  --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2, development:

```sh
cd ~/Projects/stress-detection/web
npm ci
npm run dev
```

Open **http://127.0.0.1:3000**. Camera permission is requested only by Start camera. Audio is never requested. The frontend proxies `/api/local/*` to the loopback backend; no external service is involved. Use port 3000: mutation-origin checks intentionally allow only `http://127.0.0.1:3000` and `http://localhost:3000`, with an app request header.

Production presentation alternative (stop the development server first):

```sh
cd ~/Projects/stress-detection/web
npm ci
npm run build
npm run start
```

Leave the Python service running. Do not run development and production servers on the same port. Do not expose these servers publicly; the application is a local single-computer workspace, not an authenticated multiuser service.

## What functions

| Area | Implemented behavior |
|---|---|
| Public website | Photographic home, interactive product guide, about, resources, privacy, responsive navigation/drawer, footer and actual research results |
| Dashboard | Real first-use state, current in-memory session, resume questionnaire, explicitly saved recent sessions and fresh-session reset |
| Questionnaire | Seven standard items, two-week timeframe, back/next/review, all answers required, sum 0–21, published bands, optional unscored difficulty context |
| Camera | Explicit Start, visible preview/timer/Stop, fixed Stop dock, automatic stop near 35 seconds, retake/discard/download, optional prerecorded file, explicit local Analyze action |
| Analysis | Genuine native face/pulse child processes, one active analysis at a time, idempotent job creation, real polling stages, cancellation and sanitized failure states |
| Results | Separate questionnaire result and all supported/null camera observations; every Green/POS region/window displayed with rejection and band-edge flags |
| History | Explicit browser opt-in, reopen, date filters, delete, and trend only for questionnaire scores on at least two distinct days |
| Reports | JSON download and print/save-PDF view from the same session values; source, quality, software/model versions, optional note and screening explanation |
| Wellbeing | Adjustable paced-breathing start/pause/reset, grounding checklist, optional saved/deletable private note; described as general wellbeing, not treatment |
| Settings | Ivory/evening theme, reduced motion, browser export/delete, server-recording list/delete and complete local-server cleanup |
| Research | Actual locked comparisons for six models and both outcomes; limitations and unconfirmed external exposure history; no deployment selection |

Questionnaire scoring is entirely browser-local. `web/lib/gad7.json` is shared with the validated backend scoring endpoint; the UI does not need to transmit answers. Published bands are 0–4 minimal, 5–9 mild, 10–14 moderate and 15–21 severe. Source/permission details and the retained developer attribution are in the asset/instrument document. GAD-7 categories are not UBFC CSAI dimension means.

## Actual storage and deletion

- Default browser state: answers, current score, observations and session note live only in React memory. Reload/close clears them. Ordinary app navigation preserves the current session.
- Save session: explicit localStorage opt-in stores score, observations, date, optional note/difficulty and a retained recording reference, **not raw item answers**. This is not encrypted. History is never seeded with sample sessions. Theme/motion preferences are persisted when changed. Private notes are saved only by their Save button.
- Camera data: MediaRecorder first makes a browser Blob. Only Analyze sends it to the local server. Preselected prerecorded videos are not automatically submitted. There is no cloud upload or third-party analytics. Font and photo requests stay on the local origin.
- Server files: only the app-owned ignored `data/processed/still-local/` tree. Native intermediates and source upload are deleted after completion/failure unless the user explicitly keeps the recording. Runtime ownership is checked before cleanup. Job results stay in memory for at most 30 minutes; stalled uploads/jobs expire. On startup, stale temporary jobs are removed. Explicitly retained recordings remain across restarts until deleted.
- Cancel/navigation exit stops camera tracks, aborts upload/polling, and requests deletion of the known job. A whole-browser crash or connection loss can prevent confirmation; TTL/startup cleanup is the fallback. Failed deletion is not reported as success. Camera hardware checks remain pending below.
- History deletion removes the browser record and its linked retained recording when the backend is reachable. Settings can remove all server jobs/recordings and browser sessions/notes/current answers. Browser-only deletion is offered separately when the service is unavailable.
- User-downloaded reports/recordings and saved PDFs are outside app control: delete them manually. No sensitive answers are put in URLs, analytics, access logs or validation errors. Run uvicorn with `--no-access-log` as shown.

The API accepts video uploads up to 100 MiB and rejects recordings over four minutes/10,000 decoded frames. Queue limits, duplicate-upload guards, fixed server filenames, UUID-only deletion, origin/header checks and a background child-process group bound the local workflow. These are not claims of public-service security.

## Presentation walkthrough

1. Start both servers. Open Home and demonstrate the product-guide tabs, privacy explanation and FAQ. Open Your space: the empty dashboard is genuine.
2. Begin the GAD-7 flow, emphasizing the last **two weeks**. Enter your own presentation/test responses explicitly; do not present those as participant data. Review all seven. Show the questionnaire-derived score/category and its screening explanation.
3. Camera is optional. Open Camera session. Explain the 35-second target and missing-measurement policy. Click Start, show the timer and Stop, then explicitly choose Analyze. Until processing completes, no live pulse or face value is shown.
4. Review separate sources in Results. Explain rejected readings rather than hiding them. Demonstrate the software/version disclosure, JSON download and print preview; compare the same displayed/exported score.
5. Explicitly save the session; reopen it from History. Show filters and deletion. Show that no raw item answers are saved. The trend requires distinct saved days; do not create fake history or treat same-day scores as momentary change.
6. Try paced breathing and a grounding checklist. A note only persists after Save. Show Settings and its explicit deletion controls.
7. Open Research: the actual facial cognitive improvement was tiny and inconsistent; no model beat mean for somatic errors. These models are not used in the assessment. The site is a presentation/research tool, not live anxiety validation.

## Honest prerecorded fallback

A private 35.3-second, 512-pixel excerpt from an existing **development-only** recording was processed successfully here. It is not bundled, served as a static asset or committed. Choose it explicitly under Camera → Use a clearly labeled prerecorded input:

`data/processed/still-validation/development-prerecorded.mp4`

The UI and exported report mark it **prerecorded**, not live. A fresh fallback can be prepared without altering its source:

```sh
.venv/bin/python scripts/prepare_still_demo.py \
  --input data/raw/UBFC-Phys/s25/vid_s25_T1.avi \
  --output data/processed/still-validation/development-prerecorded-new.mp4
```

The command requires an already available, consented input, refuses overwrite, hashes its source/output and saves a provenance receipt. It encodes a short excerpt with PyAV/libx264 and carries source-frame PTS into the encoder. Resulting container timestamps are not independent camera/wrist ground truth. This excerpt supports observation testing only; it is never passed to a session-anxiety regressor. No new dataset is downloaded.

## Validation and measured conditions

Verified in this workspace:

- **157 Python tests passed**, including seven new app tests for all 22 totals/category boundaries, incomplete/invalid responses, origin/error redaction, duplicate jobs/uploads, upload limits, asynchronous dispatch, cancellation, launch failure and actual deletion of owned files.
- **11 production Playwright tests passed**, including questionnaire/review/export agreement, save/reopen/filter/delete, permission denial only after Start, backend offline, interrupted-job cancellation, notes/tools/theme/reduced motion, layouts at **390/768/1440 px**, mobile drawer Escape, keyboard product tabs/radio navigation, semantic assessment progress, and automated WCAG A/AA/2.1-AA checks with no reported violations after fixes. Additional completed scans cover assessment, camera, tools, settings and research. Page transitions preserve text opacity/contrast.
- Browser-to-Python upload processed the real development excerpt: one complete window, six screened region/method estimates. Direct local-service processing took about **11.15 seconds** for this 35.3-second 512×512 input, including upload/polling. It is not an accuracy measurement or a guarantee for another input/device.
- A visibly labeled **synthetic test camera** exercised actual browser MediaRecorder, 35-second automatic stop, track cleanup, real WebM upload and native Python analysis. A real blank-video pipeline test returned all-null facial/pulse values. These test fixtures are not shipped as live measurements.
- TypeScript, the **Next.js production Turbopack build**, `pip check`, and validation of the completed locked anxiety evaluation all passed. Existing experiment/source hashes remain compatible. No scientific model was trained or changed.
- Three fresh headless Chromium browser contexts against local production, 1440×1000, no throttling: **TTFB 1.4–1.6 ms; observed LCP 64 ms; approximately 458 kB resource transfer and 271 kB JavaScript transfer**. Host caches may be warm and validation jobs were running. These are local diagnostics, not network/mobile benchmarks or Lighthouse scores. No zero-lag claim is made.

Private evidence and screenshots are under ignored `data/processed/still-validation/`: `performance.json`, `development-flow.json`, `no-face-flow.json`, `accessibility-final.json`, and `screenshots/`. No participant image or sensitive screenshot is staged.

Recheck with both production servers running:

```sh
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m pip check
npm --prefix web run typecheck
npm --prefix web run build
npm --prefix web test
```

The real-development-file browser test is explicitly skipped on machines where the private clip is absent; it ran and passed here. Use the fallback preparation command to reproduce locally. All other fixtures are labeled test-only, not production sample data. No Lighthouse score was run or claimed.

## Remaining manual checks

- **Physical webcam/OS permission and camera LED check: pending.** Headless synthetic capture verifies the browser/container path, not physical hardware. On the presentation laptop, grant real permission, record, Stop, navigate away and verify the LED/tracks stop. Revoke permission and repeat.
- Test the actual device's lighting, skin appearance, glasses, pose, multiple people and high movement. The frozen detector/gap tests cover invalidity rules, but this is not validation of real-world pulse accuracy. Do not change thresholds to make a demo look successful.
- Verify Safari/Firefox and their MediaRecorder codecs if those browsers will be used; current browser QA is Chromium. Check camera selection and physical mobile capture separately.
- Inspect an actual browser print dialog/PDF and downloads folder on the presentation OS; JSON consistency is automated, print CSS is implemented, and exported files remain user-managed.
- Manual screen-reader review remains useful beyond automated accessibility/keyboard checks. This is a local single-user app with unencrypted opt-in storage, not a production clinical service.
