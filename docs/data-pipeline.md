# Streaming video timing and private manifests

These commands inspect originals without modifying them. They do not extract
facial/pulse features, train models, or establish video-to-sensor alignment.
The existing sample validator, reader CLI, and manifest builder share the same
`inspect_video` implementation; numeric CSV checking is reused as well.

## Commands

From the repository root:

```sh
source .venv/bin/activate
python -m pip install -e '.[inspection]'
python -m unittest discover -s tests -v
python -m stress_detection.manifest data/raw/UBFC-Phys \
  --output data/processed/ubfc-phys/manifest-new.json
python -m stress_detection.video_reader data/raw/UBFC-Phys/s25/vid_s25_T1.avi \
  --output data/processed/ubfc-phys/reader-T1-new.json
```

Choose a new output filename for each run. Reports must be Git-ignored files
under this project's `data/processed/`. Existing output files are never
overwritten. Reports from this milestone are in the local ignored
`data/processed/ubfc-phys/timestamps/` directory. Do not commit them. The manifest
streams every discovered uniquely paired video, not merely its header; hashing
and decoding the full sample involves reading roughly 13 GiB of video twice.
The standalone reader command is an optional single-video diagnostic using that
same inspection routine. The original `stress_detection.validate_sample`
command remains available and additionally checks personal-file structure and
saves local visual-inspection copies; manifests never read those personal files.

## Reader API and timing semantics

```python
from pathlib import Path
from stress_detection.video_reader import VideoReader

with VideoReader(Path("data/raw/UBFC-Phys/s25/vid_s25_T1.avi")) as reader:
    for frame in reader:
        # frame.rgb is a PyAV rgb24 VideoFrame at original resolution.
        # Use the frame here; do not collect all frames in a list.
        original_pts = frame.pts
        original_time_base = frame.time_base
        original_seconds = frame.presentation_time_seconds
        relative_seconds = frame.relative_time
        # It is safe to break early: exiting with closes the decoder/container.
        break
```

Each yielded record contains zero-based decode index, RGB frame, original
decoder-reported integer PTS, rational time base (`Fraction`), exact presentation
time `PTS * time_base`, relative time, optional separate fallback time, corruption
flag, and timing issues. Presentation-time seconds are a float convenience;
the fraction is retained for exact comparisons. Relative time subtracts the
first valid presentation time, whose original PTS, time base and frame index
remain recorded in the summary. No origin is silently reset to zero.

“Original” here means timing reported by PyAV/FFmpeg for the input, including
container/demuxer timing. AVI demuxing can derive timing from stream structure;
these values are **not proof of independently captured camera timestamps**.
There is no Python substitution of index divided by nominal FPS. Frame objects
are converted to RGB only in memory; original bytes are read-only.

Missing PTS/time bases leave original presentation time `None`. If needed for a
separate engineering experiment, explicitly pass `fallback_fps` and optionally
`fallback_origin` to `VideoReader`. Only untimed frames get `fallback_time =
fallback_origin + index / fallback_fps`; their original PTS/time remain missing.
Fallback time is never mixed into the original timing audit or used by the
manifest/inspection commands. Its FPS and origin are labeled in the summary.

Adjacent identical presentation times are counted as duplicates; decreasing
times as nonmonotonic. A nonadjacent repeat that moves backward is detected as
nonmonotonic rather than maintaining an unbounded history of all timestamps.
Missing timing breaks adjacency; no spacing is fabricated across it. A spacing
over 1.5 times the stream's nominal interval is a gap warning; a deviation over
the larger of 1 microsecond or 1% of that interval is irregular. These are
engineering diagnostics, not proof of dropped acquisitions; variable-rate media
may legitimately trigger them. Comparisons use exact rational times, even if
the frame time base changes.

The audit retains counters, extrema, a running mean and at most 20 examples.
There is no video-sized RGB/PTS list. Decoding uses one thread and no application
prefetch queue. The reader closes on exhaustion or decoder failure; a context
manager or explicit `close()` is required for early stops and consumer errors.
Do not retain frames if bounded application memory is required. An early-exit
summary is explicitly incomplete and cannot validate a whole recording.

Duration fields are intentionally distinct:

- `pts_span_seconds`: last valid presentation time minus first valid time.
- `observed_duration_seconds`: PTS span plus the last decoded frame's reported
  duration; unavailable when that duration is unavailable. This includes gaps,
  without pretending all intermediate timestamps exist.
- `stream_duration_seconds` / `container_duration_seconds`: metadata extents.
- `decoded_duration_at_nominal_rate_seconds`: frame count divided by reported
  average FPS, explicitly a nominal estimate.
- `pts_span_plus_nominal_frame_seconds`: endpoint-span estimate using a nominal
  final-frame interval; never silently substituted for observed duration.

Missing/duplicate/backward timestamps, corrupt frames, decoding failures and
declared/decoded frame-count mismatch fail video validation. Gap/spacing and
observed/declared duration discrepancies require review. The existing validator
retains its structural checks; the manifest treats timing warnings as
`needs_review`. Matching video and reference durations **does not establish
video-to-sensor synchronization**, a common origin, or absent sensor drift.

## Manifest schema 1.0

Discovery recurses through actual participant directories, including enclosing
download wrappers. Paths are relative to the dataset root supplied on the
command line, not the machine or repository root. Only recording files are
inspected: videos, BVP and EDA. Names are checked against directory participant
IDs; documented task conditions are stored separately from empty
`classification_labels`. No stress classification labels are invented.

Each recording contains:

- Stable `participant_id/task_id` recording ID; participant/task identifiers,
  documented `task_condition`, and `synchronization: unverified`.
- Candidate video/BVP/EDA paths, retaining missing/ambiguous pair information.
- Unique file paths, byte counts and SHA-256 fingerprints. Hashing streams data
  in bounded blocks and source size/mtime are checked around inspection; mtime
  itself is not recorded. Hashing establishes local identity, not source trust.
- Shared video validation and timing summary; numeric signal shape, counts,
  documented BVP 64 Hz / EDA 4 Hz, nominal durations and errors.
- Observed-video versus nominal-reference duration differences. Signal time is
  count/rate-based only; sample-index origin and alignment are unverified.
- Validation status, sorted warnings, and split role. The existing sample is
  `development_only`; other participants start `unassigned`.

The manifest has `schema_version`, dataset name, sorted recording list, discovery
issues and overall status. It contains no generated wall-clock timestamp,
absolute source root, questionnaire values, sex, scenario assignment, experiment
date/time, or personal metadata. Runtime decoder text that might embed absolute
paths is omitted in favor of structured diagnostics/counts. For unchanged files
and the same decoder version, ordering and content are deterministic; a decoder
upgrade can change inspection results and should be recorded separately.

The three documented tasks are expected for every discovered participant, so a
wholly absent task is reported rather than disappearing. Extra tasks remain
visible with an undocumented-task warning. Duplicate participant directories,
multiple candidates (including browser-style copy suffixes), ID mismatches,
symlink sources, and unexpected recording names require review. Ambiguous pairs
are never silently resolved; the report retains all candidates and exits nonzero
when review is required. No participant is automatically dropped.

## Split validation, without fabricating a cohort

The builder does not create an evaluation split. The current one-person sample
stays development-only; it is explicitly barred from final-test assignment.
For an independently planned future cohort, supply a private assignments JSON:

```json
{
  "schema_version": "1.0",
  "participants": {
    "train": ["s901"],
    "validation": ["s902"],
    "test": ["s903"]
  },
  "recordings": [{"recording_id": "s901/T1", "split": "train"}],
  "windows": [{"window_id": "example-window", "recording_id": "s901/T1", "split": "train"}]
}
```

**These identifiers are synthetic schema examples, not an actual cohort or a
sufficient sample size.** They will be rejected as unknown against the current
real manifest. Never copy this into a purported real evaluation split.

All known participants must be assigned exactly once in a supplied assignments
file. Recording/window assignment lists are optional assertions: all recordings
already inherit the participant's split. If supplied, each recording/window ID
must occur once, refer to a known recording, and agree with its participant's
role; an optional asserted participant ID must also match. Windows inherit roles
through `recording_id`; never split windows independently of that mapping.

Once a real, justified cohort plan exists, validate it with:

```sh
python -m stress_detection.validate_splits \
  data/processed/ubfc-phys/cohort-manifest.json \
  data/processed/ubfc-phys/cohort-assignments.json \
  --output data/processed/ubfc-phys/cohort-split-check-new.json
```

This conditional command requires those private cohort files; none is invented
for the current participant. Alternatively pass `--splits` to the manifest
builder. Overlap, unknown IDs, duplicate assignments and participant leakage
return a nonzero exit status. Empty roles and fewer than three participants
produce explicit warnings. A structurally valid split never establishes
statistical sufficiency. Do not use the validator to justify one-person model
evaluation. No windows or features are created by these commands.

## Verification scope

Synthetic tests cover nonzero origins, fractional time bases, variable spacing,
missing/duplicate/backward PTS, gap-aware window indexing, explicit fallback,
bounded diagnostic storage, decoder/consumer failure and early resource cleanup.
Tiny generated lossless videos exercise PyAV decoding and the shared inspector.
Manifest/split tests cover missing/ambiguous pairs, ID mismatch, duplicate
participant directories, privacy/order/hash behavior, overlapping participants,
unknown IDs, duplicate recording/window assignments, and cross-split windows.
No real participant file or derived output is used as a committed test fixture.

The local sample manifest passed for all three tasks: each video decoded 6,325
frames with original decoder-reported PTS 0–6324 and time base `500/17569`.
Presentation-time range is 0 to 179.976094257 seconds; spacing is uniformly
0.028459217941 seconds, matching the reported 35.138 fps. No missing, duplicate,
backward, gap or irregular-spacing warnings were found. Extent including the
last reported frame duration is 180.004553475 seconds, approximately 4.55 ms
longer than each nominal 180-second BVP/EDA recording. The paper's rounded 35 fps
must not replace the actual time base. Those structural observations do not
establish video-to-sensor synchronization or psychological validity.

Synchronization verification, broader acquisition, and all feature/model work
remain pending under the [research protocol](research-protocol.md).
