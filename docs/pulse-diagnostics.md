# Frozen pulse diagnostic audit

Checked 2026-11-10. This is an engineering audit of the existing development
sample, not a physiological validation or a method/region selection exercise.
All participant traces, plots, peak values, per-window tables and camera edge
annotations remain under ignored `data/processed/ubfc-phys/pulse-diagnostics-reviewed/`.
The original face-quality and pulse-baseline runs remain unchanged. The initial
diagnostic outputs were also retained separately. Reproduction commands and
output definitions are in [pulse-baseline.md](pulse-baseline.md#frozen-diagnostics-command).

## Findings and limits

The evidence points to **ambiguous reference spectra with an unresolved physical
cause**, rather than a reproduced implementation defect. Every saved BVP
summary and camera-window row reproduced exactly. The audit checked nominal
64 Hz BVP sampling, unique recording/task and source-hash pairing, reference
checksum, half-open complete 30-second windows, no cross-task samples, linear
detrend, symmetric Hann taper, unpadded real-FFT axis and Hz-to-BPM conversion.
Independent diagnostic spectra matched production peak fractions and estimates.
Synthetic fixtures independently check the rate/Nyquist axis, known frequency
and BPM, drift, multiple reference windows and discarded trailing samples.
No baseline implementation fix was justified; `pulse.py`, its settings and the
original results were preserved. Only the diagnostic command and tests were added.

T2 reference failures are exactly `diffuse_spectrum`: the largest in-band bin
does not contain the fixed minimum fraction of total in-band power. They are
not failures of numeric parsing, sample availability or the flat-signal guard.
The inspected raw/detrended traces contain irregular transient excursions and
changing amplitude, with competing in-band maxima and substantial sub-band
structure. Removing a fitted straight-line trend leaves those features visible.
The candidate winners are not simply pinned to the search boundary; narrowing
the explanation to an edge-selection problem would miss the diffuse spectra.

T1 has more repetitive traces and more concentrated in-band peaks, while T3
contains both passing and diffuse spectra, large excursions and a passing
reference candidate near the lower band edge. Passing windows can visibly
contain transients and competing maxima. Thus the existing acceptance screen
does not establish artifact-free reference data or identify a physiological
fundamental. Do not reinterpret a passing median as ground truth.

No sustained exact flat segments or repeated window-extremum plateaus were
observed. Large adjacent steps are measurable, but no step-size rejection
threshold was introduced. CSV quantization, filtering, units and hardware rails
are not documented, so absence of repeated extrema does not rule out upstream
clipping. Apparent low-frequency variation is not proof of slow sensor drift.
Motion or wrist-contact changes could explain transients, but the retained
signals do not independently establish either. Do not attribute failure to
speech motion merely because the task is speech.

Camera failures retain their original distinctions: diffuse spectra, unsupported
long gaps and insufficient valid RGB are separate reasons. Accepted camera
estimates near the lower search edge are flagged in private reports for T2 and
T3. These flags do not alter coverage, relax thresholds, recover rejected BPM,
or select green/POS or any ROI. Agreement with this participant cannot justify
a new method, band, region or rejection rule.

## Official timing evidence

The refreshed official DataPort `READ_ME.docx` confirms per-task file naming
and 64 Hz BVP. It provides no retained CSV sample-zero or video-frame mapping.
The original paper, Sections 2.2–2.3, explicitly describes experimenter-announced
task boundaries and participants pressing the E4 button with the wrist visible
to the camera, using bracelet event markers to facilitate synchronization.
It also describes continuous session video capture and retained task segments:
middle three minutes for rest, initial three minutes for speech/arithmetic.
Sources: [official DataPort documentation](https://ieee-dataport.org/open-access/ubfc-phys-2),
[original paper at the authors' university laboratory](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf),
[DOI](https://doi.org/10.1109/TAFFC.2021.3056960).

This is explicit evidence of an acquisition synchronization mechanism. It does
not specify the retained files' event timestamps, exact trim indices, CSV
sample-zero correspondence, residual offset/drift or dropped-sample handling.
The local single-column files and manifest do not supply that mapping. Therefore
the [synchronization gate](research-protocol.md#pulse-reference-synchronization-gate--pending)
remains pending: independent recording-level medians and coverages only, with
null differences when either accepted set is empty. No paired-window errors,
waveform/beat agreement or trace-fitted offset was computed. A future alignment
audit needs retained marker logs/trim mappings or equivalent independent evidence;
do not infer them from equal durations or optimize agreement on these traces.

## Proposed multi-participant engineering pilot

This is the next separately authorized step; no additional participants were
downloaded and no model was trained. Keep s25 development-only. Follow the
[protocol acquisition/storage and partition rules](research-protocol.md), with
at most two additional participants per transfer batch, all tasks retained.
Batch size is a storage constraint, not a sufficiency claim.

1. Inventory official archive sizes, scenario strata, availability and terms.
   Freeze an acquisition order independent of pulse quality or agreement. Retain
   unavailable and structurally excluded candidates with reasons. Before each
   transfer, remeasure disk space and budget retained archives, extracted members,
   derived outputs, active extraction and the protocol's OS reserve. Do not
   automatically delete source archives.
2. For each archive, record its hash and compressed/uncompressed member sizes;
   reject unsafe paths, duplicate members, symlinks and participant-ID conflicts.
   Extract exclusively into a new ignored destination, read members fully to
   verify CRCs, and preserve the original archive. Process one participant/task
   at a time with bounded video decoding; stop the batch on structural failures
   rather than silently renaming or substituting files. These are workflow
   requirements. The subsequent [local pilot runner](pilot-runner.md) implements
   resumable sequential orchestration and safe local archive extraction; it does
   not acquire archives or perform model training.
3. Run existing sample validation and manifest generation. Save a private batch
   inventory keyed by participant/task and hashes. Freeze participant roles
   before cohort windowing: all tasks and later derivatives inherit their
   person's role. The pilot must remain exploratory if disjoint evaluation and
   validation roles lack adequate independent participants.
4. Reuse completed full face-quality runs where provenance matches; otherwise
   extract once per recording. Run the frozen pulse baseline, then
   `pulse_diagnostics` for every task. Give each stage a new output directory,
   and log command, software/code/model/input hashes, settings, start/end/status
   and output paths. Resume only completed matching stages; retain failed
   attempts and schedule every eligible complete window across all methods.
5. Automatically audit numeric validity/rates/counts/trailing samples; PTS
   consistency, gaps and final extent; pairing and checksums; source/grid
   availability and rejection reasons; camera and BVP edge candidates; strongest
   bins/local maxima, peak fraction and threshold margin; below-band power,
   linear trend, adjacent-step quantiles/maxima, exact runs and repeated extrema.
   Save raw/detrended/spectral plots for every reference window. Do not convert
   these descriptive statistics into new gates after inspecting one participant.
6. Review anomalous spectra and representative passing windows on development
   participants. Summarize equal-participant coverage, failure/edge frequencies
   and costs by task/scenario, retaining missing/empty results. Record unresolved
   physical causes and synchronization status separately. Do not select the
   region or method with smallest reference difference. Any changed baseline
   requires a versioned development-only rationale and a fresh prospective run.

Before training, require structural integrity and unique pairing, reproducible
completed extraction with complete failure denominators, frozen participant
roles and leakage checks, documented feature units/missingness policy, a frozen
development-justified quality policy, and feasible grouped validation. Audit
task/scenario-dependent rejection and edge prevalence before admitting pulse
features; resolve or explicitly prespecify handling of unreliable pulse rather
than hiding failures. Preserve the protocol's quality-only and motion/pose
controls and training-only learned preprocessing. Confirm independent timing
evidence and reference validity **before paired physiological validation**;
until then restrict reference comparisons to recording level and make no pulse
accuracy/HRV claim. Training and further acquisition remain separate decisions.

Verification: the full synthetic suite and dependency consistency check passed;
the diagnostics reran all three recordings and matched all saved decisions.
Staged files were inspected for data leakage; only code, synthetic fixtures and
nonidentifying documentation were committed.
