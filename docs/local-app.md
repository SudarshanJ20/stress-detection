# Still — Anxiety Screening & Wellbeing

A complete local major-project presentation for “Anxiety Screening and Webcam-Based Physiological Monitoring.” The app supplies a **questionnaire-derived GAD-7 screen** and separately attributed **camera observations**. It does not deploy the anxiety regressors, combine the sources into a score, or claim diagnosis or validated live anxiety assessment. Completed experiments, scientific modules, frozen configurations and model artifacts are preserved.

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
