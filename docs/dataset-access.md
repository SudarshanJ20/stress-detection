# UBFC-Phys access investigation

Checked **2026-11-08**. One user-downloaded participant archive has now been
extracted and inspected locally. The sample-access checkpoint covers file
availability, CRCs, numeric structure, full video decoding, and sparse visual
inspection; synchronization remains unverified. Dataset selection remains
provisional. No licenses were accepted or applications submitted on the user's
behalf.

## Official sources and inspection results

| Source | Official URL | Result |
| --- | --- | --- |
| Author's dataset page | https://sites.google.com/view/ybenezeth/ubfc-phys | Read; links both download hosts and the paper. |
| IEEE DataPort dataset | https://ieee-dataport.org/open-access/ubfc-phys-2 | Public HTML inspected directly over HTTPS; web reader could not fetch it. File access is login-gated. Dataset DOI: `10.21227/5da0-7344`. |
| Dataset documentation | DataPort page, **DOCUMENTATION → READ_ME.docx** | Public 7.4 KiB document downloaded to temporary storage and read using standard-library ZIP/XML tools. Not committed. Use the page to obtain its current link; the document URL expires. |
| Original paper | https://doi.org/10.1109/TAFFC.2021.3056960 and https://ieeexplore.ieee.org/document/9346017 | Publisher's indexed article text inspected; direct Xplore requires JavaScript/robot verification. Published online in 2021; journal issue 14(1), 622–636, 2023. |
| Author-linked paper copy | https://drive.google.com/file/d/1M39d0MnIlHGtGtzbxle8DRp3aHMg8bCF/view | Viewer/loading page; PDF download was not obtained from this route. |
| Authors' university laboratory paper copy | https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf | Downloaded and read on 2026-11-10; explicit trigger evidence noted below. Not redistributed. |
| University download route | https://search-data.ubfc.fr/FR-18008901306731-2022-05-05_UBFC-Phys-A-Multimodal-Dataset-For.html | Author-linked official route, but returned Anubis access denied. Contents, license, sizes, and download granularity could not be inspected. |
| License linked by DataPort | https://creativecommons.org/licenses/by/4.0/ | Inspected; dataset metadata explicitly links CC BY 4.0. |

The original paper is Meziati Sabour, Benezeth, De Oliveira, Chappé, and Yang,
*UBFC-Phys: A Multimodal Database For Psychophysiological Studies Of Social Stress*.
Publisher indexed text was available at
https://xplorestaging.ieee.org/document/9346017 through search, but direct requests
returned HTTP 418. Protocol details below are supported by the dataset README
unless explicitly attributed to the paper. No unofficial mirrors were used.

## Verified organization, signals, and labels

The README describes 56 participant folders, `s1` through `s56`. For participant
`N`, the documented layout is:

```text
sN/
  info_sN.txt
  vid_sN_T1.avi
  vid_sN_T2.avi
  vid_sN_T3.avi
  bvp_sN_T1.csv
  bvp_sN_T2.csv
  bvp_sN_T3.csv
  eda_sN_T1.csv
  eda_sN_T2.csv
  eda_sN_T3.csv
  selfReportedAnx_sN.csv
```

This documented schema matches the inspected local sample: one `s25/` folder
with 11 files. The download browser also lists outer folders named `sN_zip`;
individual-file delivery through that interface remains unverified.

| Field | Documented meaning |
| --- | --- |
| `T1` | Rest task |
| `T2` | Speech task |
| `T3` | Arithmetic task |
| `test` / `ctrl` | Two difficulty scenarios, randomly assigned per participant; recorded in `info_sN.txt`. These are experimental conditions. |
| BVP | Empatica E4 contact blood-volume pulse reference, **64 Hz**, matched by participant and task |
| EDA | Empatica E4 electrodermal activity, **4 Hz** |
| `info_sN.txt` | Sex code (`m`/`f`), assigned scenario, experiment date, and start time |
| Questionnaire | Pre-session and post-session cognitive anxiety, somatic anxiety, and self-confidence scores |

The questionnaire CSV is documented as a **3 × 2** matrix: rows are cognitive
anxiety, somatic anxiety, self-confidence; columns are pre-experiment then
post-experiment. These are session-level self-reports, not per-task or per-frame
measurements. Neither task identity nor difficulty assignment is a confirmed
stress diagnosis. Do not substitute a task label for a measured psychological
outcome or assume every participant responded in the intended direction.

The paper reports 35 fps, 1024 × 1024 Motion JPEG video and three retained minutes
per task: the middle three minutes for rest, and the initial three minutes for
speech and arithmetic. It describes CSAI-based questionnaires, with 7 cognitive,
7 somatic, and 9 self-confidence items rated 1–4. The inspected sample has the
documented resolution and codec, but its reported frame rate is 35.138 fps rather
than the rounded 35 fps; see the validation summary. A subsequent complete
reading of Section 2.2 is recorded in the timing update below; the unmodified
TSST protocol must not be assumed to apply.

The README does not establish CSV header/timestamp conventions, units for BVP,
sample counts, missing samples, or exact video/reference alignment. Local
sample checks below establish numeric structure and counts, but cannot establish
that no acquisitions were lost upstream. Nominal duration and sampling rate
alone do not prove synchronization.
Public DataPort comments report possible filename issues for s40 and s56; those
are user reports, not verified corrections. Avoid those participants initially
and audit identifiers rather than silently renaming files.

## Download routes and access requirements

**Best verified entry point: the official DataPort page.** Its public file list
advertises `s1.zip` through `s56.zip`, with individual sizes, and corresponding
restricted `s1_zip` through `s56_zip` folder entries. Thus participant-sized
packages are advertised; there is no evidence that a single full-dataset archive
is mandatory. Individual recording access is **not yet verified**. Folder entries
suggest a possible finer-grained route, but their presence does not establish
which files or download operations are available after login. ZIP link delivery
also has not been tested.

The dataset-specific access notice says all logged-in users can access this
open-access dataset with a **free IEEE account**, without IEEE membership. No
research application, author approval, or download payment is stated there.
The HTML also includes a generic subscription modal; this is not proof that this
open-access dataset requires a paid subscription. Verify the actual flow after
login and stop if it requests payment or additional approval.

The DataPort page names Creative Commons Attribution and its structured metadata
links **CC BY 4.0**. That license permits sharing and adaptation, including
commercial use, subject to attribution, a license link, indication of changes,
and no added legal/technical restrictions. It does not automatically clear
privacy, publicity, or other rights. The author page also requests citation of
the paper. No dataset-specific noncommercial or no-redistribution clause was
visible in the inspected public material; check any accompanying terms after
login. This project's stricter rule remains: never commit participant data or
redistribute participant files through this repository. Do not treat the dataset
license as a license for the hosting website or every accompanying document.

The university route is an official fallback, but its requirements and payloads
are unknown because of the browser protection. Do not bypass it. Author contact
details are provided on the dataset page if clarification is needed; no contact
was made on the user's behalf.

## Smallest useful sample and storage

**Smallest conceptual sample:** one participant/task video plus its corresponding
BVP CSV, `info_sN.txt`, and the official README. Include the questionnaire CSV to
interpret measured outcomes. Individual-file byte sizes and accessibility remain
unknown. EDA is optional for the planned camera/pulse smoke check.

**Preferred first sample:** all three tasks from **s25**, with matched BVP, EDA,
participant metadata, questionnaire, and README. The smallest publicly advertised
participant package is **`s25.zip`, 12.85 GB**. This is the smallest listed package,
and has now been obtained by the user and inspected locally. This confirms
availability of that participant package, not individual-file download support.

Verified DataPort listing figures:

- 56 ZIP entries, ranging from **12.85 GB** (`s25.zip`) to **16.98 GB** (`s11.zip`).
- Summing the displayed rounded sizes gives **792.50 GB** in the page's units.
  This is a calculation from published labels, not measured transfer bytes.
- Extracted sizes and ZIP member sizes are not documented in the inspected
  public README/page. Whether listed ZIPs and expanded folders represent the
  same bytes is unverified. Compression ratios are unknown.

Do not assume the full dataset fits in approximately **767 GiB free**. If the
page uses decimal GB, the advertised download total is about **738.1 GiB**, leaving
only about 29 GiB before extraction, workspace, and OS needs. If the labels use
binary units, even the downloads exceed the available space. Both interpretations
make a full download plus extraction inappropriate without measured sizes and
additional storage.

For s25, 12.85 decimal GB would be about **11.97 GiB**; the page's unit convention
is not confirmed. Peak local storage is **archive bytes + extracted bytes +
temporary overhead**, not just the download size. A provisional **40 GiB free-space
budget** for one participant is a planning allowance, not a verified requirement
or guarantee. Recheck free space and actual uncompressed sizes before extraction.

macOS already has `/usr/bin/unzip`; no ML libraries are needed. Once a ZIP has
been obtained legitimately, local `unzip -l` can inspect member names and sizes
before extraction. Python 3.12's standard-library `zipfile` supports ZIP64.
The inspected sample uses stored/Deflate members without encryption, and all
member CRCs passed during extraction. Other archives remain untested.

**Selective remote extraction is not established.** ZIP can support selective
member reads in principle, but a remote implementation needs working byte-range
access to the actual object, its central directory, supported compression, and
valid authorization. None of these was tested for dataset objects. HTTP range
support on the HTML page says nothing about the archives. Local selective
extraction does not save the initial archive download. Use individual files only
if the authenticated official interface actually provides them; otherwise plan
to download one complete participant archive.

## Original acquisition route (retained for future participants)

1. In a normal browser, open
   https://ieee-dataport.org/open-access/ubfc-phys-2 and choose **Login** (or create
   a free IEEE account yourself). Inspect any terms yourself; no acceptance,
   payment, or application has been performed for you.
2. Open **Dataset Files → s25_zip**. Check whether it exposes one participant's
   three videos, matching signals, and metadata as individual downloads, and note
   their byte sizes. Compare with the advertised **s25.zip (12.85 GB)** link.
   First inspect only: do not start an automatic bulk download.
3. If individual files are offered, choose the complete s25 set above. Otherwise
   confirm the s25 ZIP link works and its download size before obtaining that
   single archive in a later sample-acquisition task. If neither route works,
   inspect the author-linked university URL above in the browser or ask the
   authors for an official one-participant route.
4. Keep any future downloads under ignored `data/raw/UBFC-Phys/`, with expired or
   authenticated links and credentials out of Git. Do not put credentials into
   shell arguments or commit browser session information.
5. Before extraction, inspect the archive member listing, total uncompressed
   bytes, and destination paths. After acquisition, verify all task IDs, video
   readability/frame timing, BVP counts and timing, metadata, questionnaire layout,
   alignment, and any filename anomalies. Only then mark sample verification done.

## Local sample validation — 2026-11-08

**Sample-access checkpoint complete for the checks below. Phase 2 remains in
progress because alignment and broader dataset suitability are unresolved.**
One participant supports pipeline development only; it does not support a
participant-separated training/validation/test split or a generalization claim.

- Rechecked free space, archive entry paths, duplicates, symlinks, destination
  absence, and Git exclusions before extraction. No unsafe entries were found.
- Extracted 11 files (13,836,913,516 bytes, about 12.887 GiB) into ignored
  `data/raw/UBFC-Phys/`, preserving the participant folder. Files were created
  exclusively, so existing files could not be silently overwritten. Reading
  every ZIP member to EOF checked CRCs; all passed. The source ZIP was opened
  read-only and retained unchanged (size and modification time also checked).
- Locally inspected the information and questionnaire files. The participant ID,
  sex/scenario codes, and five-line information structure are valid. Date/time
  separators are underscores (`YYYY_MM_DD`, `hh_mm_ss`), unlike the README's
  hyphens. Questionnaire shape is 3 × 2 with finite numeric values, matching the
  documented dimension rows and pre/post columns. No values or personal fields
  are included here. Task assignments remain experimental labels, not diagnoses.
- All six signals are headerless, single-column numeric CSVs, with no blank,
  nonnumeric, nonfinite, or malformed rows. Each BVP file has 11,520 samples at
  the documented 64 Hz; each EDA file has 720 samples at 4 Hz. Both imply a
  nominal 180 seconds per task. The files contain no explicit timestamp column;
  no timestamps were fabricated.
- All three videos are Motion JPEG, 1024 × 1024, reported 35.138 fps, with 6,325
  declared and decoded frames each and duration about 180.004553 seconds.
  Full sequential decoding found no decoder exceptions, error-level decoder
  messages, flagged corrupt frames, missing presentation timestamps, or
  nonmonotonic presentation timestamps. No original was resized or recompressed.
- Beginning, middle, and final frames of each video were inspected locally. A
  face was visible in all nine inspected frames. This is a sparse visual check,
  not a guarantee of face visibility or rPPG quality throughout each recording.
- Video minus nominal signal duration is about +0.004553 seconds for every
  task, less than one nominal video frame. There is no material duration
  discrepancy at that threshold. This does **not** verify start offset, drift,
  trigger correspondence, or physiological alignment. Do not trim, resample,
  or assume synchronization based solely on equal durations.

Detailed JSON reports and full-resolution PNG inspection copies are stored only
under ignored `data/processed/ubfc-phys/`. Extraction details are in
`extraction.json`; the final run is in `inspection-verified/validation.json`.
Personal metadata and questionnaire scores are omitted from the validator report.
Manual visual observations are recorded separately in `visual-review.json`.
No participant files, frame images, or detailed outputs are committed.

### Reproduce validation

From the repository root, with the already extracted sample present:

```sh
source .venv/bin/activate
python -m pip install -e '.[inspection]'
python -m unittest discover -s tests -v
python -m stress_detection.validate_sample data/raw/UBFC-Phys/s25 \
  --output data/processed/ubfc-phys/inspection-new
```

Choose a **new** output directory on every run; existing output directories are
refused. The validator requires Git-ignored output under `data/processed/`, checks
all task/video/reference pairs, parses signals strictly, checks metadata and
questionnaire shape, stream-decodes every video frame, writes private JSON, and
saves beginning/middle/end previews for local review. Structural failures return
a nonzero exit status. Duration discrepancies are warnings; synchronization and
visual review are never inferred automatically. Synthetic tests cover malformed
signals, missing reference/video pairs, and metadata format variation. No real
participant values are used as test fixtures.

No existing FFmpeg/ffprobe executable was found. The optional `inspection` extra
adds only **PyAV (`av`)**, whose wheel bundles FFmpeg libraries; the verified local
version is 19.0.2. No ML dependencies, Pillow, NumPy, or standalone FFmpeg package
were installed. See [PyAV installation documentation](https://pyav.org/docs/stable/overview/installation.html).
Exact Python/PyAV/FFmpeg library versions are recorded in the private report.
The command reports container metadata and decoded presentation timing; it does
not test GPU acceleration. Disk space after extraction was approximately 741.55
GiB; recheck before future acquisitions.

### Next action

**Timing documentation update, 2026-11-10:** the official DataPort README was
downloaded again through its refreshed documentation link. The original
paper's timing sections were also read from the
[authors' university laboratory](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf),
including Sections 2.2–2.3. It documents camera-visible E4 button presses at
announced task boundaries as a synchronization aid, continuous session capture,
and different retained-segment conventions for rest versus speech/arithmetic.
This resolves the earlier lack of explicit trigger evidence; it does not supply
event logs or exact retained CSV sample/video-frame mappings. Synchronization
therefore remains unverified. See the [frozen signal audit](pulse-diagnostics.md)
for findings and the next pilot workflow. No signed download URLs or copies of
third-party documentation are committed.

The sample-access/integrity/readability milestone is complete. **Synchronization
verification and multi-participant acquisition are separate pending milestones.**
The [research protocol](research-protocol.md) now specifies evaluation targets,
participant roles, rejection comparisons, and acquisition/storage gates before
any request for further participants. The [literature review](literature-review.md)
records verified competitors and inaccessible evidence. The timestamp reader
and private manifest are implemented. The
[local pilot runner](pilot-runner.md) now provides resumable execution and exact
dry-run commands. Its availability-conditional first new batch is s1/s2, with
archive, extraction, output and reserve budgets documented there. Additional
downloads and training remain separate future steps.

Verify exact retained-segment mappings before defining aligned windows. Resolve
whether there is a known video/BVP offset and how marker times map to retained
samples/frames; consult the authors if official documentation is insufficient.
The acquisition marker mechanism is now documented, as noted above. Wider
cohort audit, actual individual-file download support, other participants' extracted sizes, and
research novelty remain unresolved. Do not acquire the full dataset based on
this sample or start model evaluation with a one-participant split.
