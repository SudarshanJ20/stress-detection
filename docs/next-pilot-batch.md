# Next engineering pilot: s3–s6

Prepared 2026-11-11, before inspecting these participants' signals. Membership is
fixed by the requested numeric IDs: s3, s4, s5, s6, all T1/T2/T3, all
`pilot_development`. Run two sequential batches, s3/s4 then s5/s6, to retain the
protocol's maximum of two additional participants per transfer batch. Keep s25
`development_only`; the final test cohort remains `unassigned`. Four additional
people are an engineering pilot, not a sufficient evaluation cohort or a basis
for population accuracy. No acquisition or training is part of this preparation.

## Execution status

The prepared local batches have now been processed sequentially using the
unchanged `pilot-camera-v1` policy. Before each execution, local archive paths,
expected contents, declared sizes and current space passed preflight; full CRC
scans passed. Actual extraction sizes, archive preservation and output hashes
were verified afterward. Both unchanged executions subsequently resumed every
stage without new attempts and preserved identical task/window results.

The private cohort review uses the completed s1/s2 camera-continuity audit only
after explicit component/settings/source/output compatibility verification;
its historical receipts remain unstamped and unchanged. s25 stays separate.
Detailed per-task results, unexpected availability losses, overlays and all
scheduled/rejected rows remain under ignored
`data/processed/ubfc-phys/pilot-review/batch-02-03/`. No participant measurements
or plots are published here. The download-status table and provisional budget
below describe the preparation checkpoint, not current archive availability.

The [raw window feature tables](window-features.md) are now constructed and
validated under `window-features-v1`, retaining missing values, all methods/regions,
original bounds and policy/source/role provenance. Predictor-only contrasts keep
labels/IDs in separate indices and wrist diagnostics in a separate recording-level
file. No imputation, scaling, learned selection or model fitting occurred. Next,
separately scope exploratory participant-held-out baselines with explicit
quality/missingness confound checks. Synchronization remains unverified; review
ambiguity/timeout cases and condition-dependent availability before complete-case
analysis. Final test assignment and further acquisition remain separate work;
no tracker or pulse rule was changed during this pilot.

## Frozen policy

Use [`pilot-camera-v1`](../configs/pilot-policy-v1.json), canonical SHA-256
`c399e9c4c10caf9021c8132044fdff08a53589580d5e2512e83c2dd663852875`.
Its components are `decoded-pts-v1`, `bounded-reacquire-v1`, and
`green-pos-baseline-v1`. [Runner semantics](pilot-runner.md) define the gates.
Complete error-free decode with present increasing original PTS and positive
final extent determines eligibility; declared count mismatch is a warning.
Keep every original window and timestamp. Require a unique unclipped return,
old-anchor association, five consecutive candidates spanning at least 0.2 s,
tighter pairwise geometry, and absence at most 2 s. Ambiguous returns stay
invalid; motion resets across segments. No pending frames are backfilled.
The unchanged pulse support limit is 0.15 s. No band, acceptance threshold,
method or region is chosen using camera/wrist agreement.

Every new receipt contains policy versions/hash in both its stamp and signed
specification. Changing policy or omitting its stamp invalidates automatic
resume. Explicit imports must pass current source/settings/completion checks.
The previous camera audit used matching numerical rules but its historical
receipts are unstamped; preserve it as audit evidence, not silently relabeled
new runs. Reuse its overlay review and synthetic continuity tests.

## Downloads to acquire separately

The public [official IEEE DataPort listing](https://ieee-dataport.org/open-access/ubfc-phys-2)
was checked on 2026-11-11 using its HTML. It advertises:

| Exact filename | Advertised size | Local status |
|---|---:|---|
| [s3.zip](https://ieee-dataport.org/open-access/ubfc-phys-2) | 14.19 GB | missing |
| [s4.zip](https://ieee-dataport.org/open-access/ubfc-phys-2) | 14.52 GB | missing |
| [s5.zip](https://ieee-dataport.org/open-access/ubfc-phys-2) | 14.11 GB | missing |
| [s6.zip](https://ieee-dataport.org/open-access/ubfc-phys-2) | 14.07 GB | missing |

Total advertised size: **56.89 GB**. Each public archive anchor opens an access
modal; it does not expose a direct public download URL. The table links to the
official listing where those exact filenames are selected after login. No
signed delivery URLs or access credentials are stored in Git. The listing also
advertises restricted `sN_zip` folders; individual-original-file delivery remains
unverified. Use the complete ZIP route for the prepared selections.

After login, check current terms/access, actual byte sizes and filenames,
transfer completion/resume support, file availability and scenario metadata.
Record scenario balance/imbalance before signal-quality inspection; keep missing
or unavailable IDs in the selection audit rather than replacing poor signals.
An advertised archive is not proof that authenticated delivery currently works.
Preserve the original ZIPs in `~/Downloads/` with these exact names. Recheck
central-directory extraction size, safe paths and expected files using the dry
run after acquisition. CRC verification happens during full extraction.

## Private selections and exact commands

Local Git-ignored files are prepared under
`data/processed/ubfc-phys/pilot-selections/`:
`batch-02-s3-s4.json` and `batch-03-s5-s6.json`. Each uses schema 1.0, the role and
prior-selection attestation above, absolute ZIP paths in `~/Downloads`, and the
unassigned final-test marker. All tasks are automatically scheduled. The
selection schema and a reproducible JSON example are in [the runner guide](pilot-runner.md).
Run from the repository root; do not change membership after quality inspection.

```sh
.venv/bin/python -m stress_detection.pilot \
  --policy configs/pilot-policy-v1.json \
  --selection data/processed/ubfc-phys/pilot-selections/batch-02-s3-s4.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-02-s3-s4 \
  --dry-run

.venv/bin/python -m stress_detection.pilot \
  --policy configs/pilot-policy-v1.json \
  --selection data/processed/ubfc-phys/pilot-selections/batch-03-s5-s6.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-03-s5-s6 \
  --dry-run
```

Both preparation dry runs exit 1 for missing archives, retain all selected IDs
and tasks, and create no runner outputs. Their private JSON reports and the
public-page snapshot are under `data/processed/ubfc-phys/next-batch-preparation/`.
The dry-run disk calculation with unavailable inputs is incomplete; use the
separate provisional storage plan below, not that partial disk subtotal.

After separate acquisition authorization and successful actual preflight,
execute the first batch and review its complete failure inventory before the
second. Repeat an execution command unchanged to resume verified stages:

```sh
.venv/bin/python -m stress_detection.pilot \
  --policy configs/pilot-policy-v1.json \
  --selection data/processed/ubfc-phys/pilot-selections/batch-02-s3-s4.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-02-s3-s4

.venv/bin/python -m stress_detection.pilot \
  --policy configs/pilot-policy-v1.json \
  --selection data/processed/ubfc-phys/pilot-selections/batch-03-s5-s6.json \
  --output data/processed/ubfc-phys/pilot-runner/batch-03-s5-s6
```

## Provisional peak storage

Measured free space before the development refresh was approximately **670.86
GiB** on the destination filesystem. Existing ZIPs, extractions and preserved
runs already reduce that number and are not charged again as future space.
After the completed s25 refresh, free space was approximately **670.25 GiB**;
the conservative all-batch budget still leaves about **373.36 GiB** beyond
its allocations. None of the four new ZIPs is on disk. Advertised GB units are not specified;
56.89 GB is about 52.98 GiB if decimal, or conservatively budget 56.89 GiB.

| Future retained/working allocation | Conservative GiB |
|---|---:|
| Four original ZIPs | 56.89 |
| Extracted originals, provisional 20 per participant | 80 |
| Derived outputs, provisional 5 per participant | 20 |
| Active workspace, once for sequential batches | 40 |
| OS free-space reserve | 100 |
| Required free before acquisition | **296.89** |

New retained data allowance is **156.89 GiB** (roughly 152.98–156.89 depending on
GB convention); including workspace and reserve needs **292.98–296.89 GiB**.
The conservative budget leaves roughly 374 GiB beyond the reserve/workspace
requirement at the initial measurement. The first two-person batch alone needs
about **218.71 GiB free before acquisition** under the same allowances. Retain
its outputs and ZIPs when assessing the second batch. These are planning
allowances, not archive-member measurements or quotas; actual extracted size,
failed attempts and transfer temporary files may require more. The 40 GiB
workspace is an allowance for active temporary work, not a second copy guarantee.
Recheck disk before every transfer and execution; after resident ZIPs have
reduced free space, the runner charges only future extraction/outputs/workspace
and reserve. Increase allowances or use approved external storage if necessary.

## Compatibility and review gates

The original s25 validation/manifest predate current completion/timing-policy
provenance, and its contiguous face settings predate bounded restarts. Refresh
validation, manifest, and the three face/pulse/diagnostic chains in a fresh
`s25-policy-v1` root; explicitly verify and reuse independent wrist estimates.
This does not retune them. The exact development refresh commands are:

```sh
.venv/bin/python -m stress_detection.pilot \
  --policy configs/pilot-policy-v1.json \
  --selection data/processed/ubfc-phys/pilot-selections/s25-policy-v1.json \
  --output data/processed/ubfc-phys/pilot-runner/s25-policy-v1 \
  --dry-run

.venv/bin/python -m stress_detection.pilot \
  --policy configs/pilot-policy-v1.json \
  --selection data/processed/ubfc-phys/pilot-selections/s25-policy-v1.json \
  --output data/processed/ubfc-phys/pilot-runner/s25-policy-v1
```

The development refresh completed successfully: only compatible independent
wrist stages were imported, and affected provenance/camera stages were rebuilt.
Original output hashes and all new receipt stamps/hashes were verified. Pulse
code/settings remain unchanged; the development output contains no pilot tasks.
All 94 synthetic tests and `pip check` pass. An unchanged dry run and execution
verified resume of every stage without new stage attempts. Detailed compatibility
decisions, hashes proving
preservation and current run results remain private under
`data/processed/ubfc-phys/policy-v1-compatibility/`. s25 contributes only to
`development_tasks`, never pilot summaries.

Before expanding further, inspect all scheduled tasks/windows including failed
or unknown schedules, decode/PTS faults, track events, face/region coverage,
long-gap rejections, camera/wrist acceptance and band-edge flags. Inspect local
ambiguous/restart/occlusion overlays. Track runtime and storage per batch; keep
originals and receipts. Compare camera and wrist at recording level while
synchronization is unverified; do not fit offsets as ground truth.

Training waits for the larger pilot review, a feasible participant/scenario
inventory, justified cohort size and participant-level role/split plan, leakage
checks, label/unit/missingness checks and a prespecified handling of abstentions.
Reference validity and synchronization remain separate gates for paired
physiological claims. Neither four additional participants nor higher tracking
coverage establishes readiness for final evaluation.
