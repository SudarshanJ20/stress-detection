# UBFC-Phys access investigation

Checked **2026-11-08**. Access research is complete for publicly inspectable
material; **no participant sample has been downloaded or verified**. Dataset
selection remains provisional. No licenses were accepted or applications submitted.

## Official sources and inspection results

| Source | Official URL | Result |
| --- | --- | --- |
| Author's dataset page | https://sites.google.com/view/ybenezeth/ubfc-phys | Read; links both download hosts and the paper. |
| IEEE DataPort dataset | https://ieee-dataport.org/open-access/ubfc-phys-2 | Public HTML inspected directly over HTTPS; web reader could not fetch it. File access is login-gated. Dataset DOI: `10.21227/5da0-7344`. |
| Dataset documentation | DataPort page, **DOCUMENTATION → READ_ME.docx** | Public 7.4 KiB document downloaded to temporary storage and read using standard-library ZIP/XML tools. Not committed. Use the page to obtain its current link; the document URL expires. |
| Original paper | https://doi.org/10.1109/TAFFC.2021.3056960 and https://ieeexplore.ieee.org/document/9346017 | Publisher's indexed article text inspected; direct Xplore requires JavaScript/robot verification. Published online in 2021; journal issue 14(1), 622–636, 2023. |
| Author-linked paper copy | https://drive.google.com/file/d/1M39d0MnIlHGtGtzbxle8DRp3aHMg8bCF/view | Viewer/loading page; PDF download was not obtained. Open in a normal browser if needed. |
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

This is a documentation-derived schema, not an inspected archive listing. The
current download browser also lists outer folders named `sN_zip`; their contents
cannot be expanded anonymously. Confirm the actual wrapper and filenames later.

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
7 somatic, and 9 self-confidence items rated 1–4. These acquisition specifications
are not verified against files. Detailed speech/arithmetic instructions and
difficulty manipulations still need a complete reading of Section 2.2; the
unmodified TSST protocol must not be assumed to apply.

The README does not establish CSV header/timestamp conventions, units for BVP,
sample counts, missing samples, or exact video/reference alignment. Those need
sample inspection. Nominal duration and sampling rate alone do not prove sync.
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
not a verified successfully downloadable sample. No sample is currently acquired.

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
before extraction. Python 3.12's standard-library `zipfile` supports ZIP64, but
the actual compression/encryption method and archive integrity remain untested.
Do not assume every archive encoding works with macOS tools.

**Selective remote extraction is not established.** ZIP can support selective
member reads in principle, but a remote implementation needs working byte-range
access to the actual object, its central directory, supported compression, and
valid authorization. None of these was tested for dataset objects. HTTP range
support on the HTML page says nothing about the archives. Local selective
extraction does not save the initial archive download. Use individual files only
if the authenticated official interface actually provides them; otherwise plan
to download one complete participant archive.

## Exact next action and unresolved checks

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
4. Keep any future downloads under ignored `data/raw/ubfc-phys/`, with expired or
   authenticated links and credentials out of Git. Do not put credentials into
   shell arguments or commit browser session information.
5. Before extraction, inspect the archive member listing, total uncompressed
   bytes, and destination paths. After acquisition, verify all task IDs, video
   readability/frame timing, BVP counts and timing, metadata, questionnaire layout,
   alignment, and any filename anomalies. Only then mark sample verification done.

Remaining blockers are authenticated file delivery and individual-file sizes,
actual archive structure/format/extracted size, complete protocol detail, and
sample quality/synchronization. Public documentation research does not resolve
these. No videos, signal files, or large archives were downloaded in this task;
no third-party document is committed.
