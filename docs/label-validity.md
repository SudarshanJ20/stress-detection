# Label validity and target decision

Audit v1, 2026-11-11. This is a source and local-metadata audit, not a new model
experiment. Existing baseline and ablation outputs are preserved. No participant
acquisition, fitting, threshold construction or cohort assignment occurred.

**Decision:** UBFC-Phys supports experimental task/condition labels and pre/post
session state-anxiety outcomes. It does not establish moment-to-moment mental
stress. Keep the completed models described as exploratory task classifiers.
For a stress-related webcam study, the strongest available psychological outcome
is a **continuous participant-session self-report**, with dimensions kept separate.
Recommend prespecifying cognitive-anxiety change as the primary outcome because
it addresses mental worry; somatic-anxiety and self-confidence changes are
secondary. This is a proposed outcome derivation, not an official stress label
or a claim that the camera can already predict it. The questionnaire adaptation
must be clarified before treating it as a validated psychometric endpoint.

## Sources actually inspected

| Source | Evidence and access boundary |
|---|---|
| [Official author dataset page](https://sites.google.com/view/ybenezeth/ubfc-phys) | Read again. Explicitly places questionnaires before and after the experiment. Links official hosts and original paper. |
| [Official DataPort entry](https://ieee-dataport.org/open-access/ubfc-phys-2) and its DOCUMENTATION → READ_ME.docx | Public HTML and the linked 7,542-byte DOCX fetched directly. ZIP/XML text inspected; the DOCX is byte-identical to the prior local inspection. Describes assignments and the 3×2 score layout. Web reader itself was robots-blocked; no login or new participant files accessed. Obtain the current documentation link from the page rather than assuming a signed URL stays valid. |
| Meziati Sabour et al., [original paper, university laboratory PDF](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf), [DOI](https://doi.org/10.1109/TAFFC.2021.3056960) | Full 15-page journal article inspected, including §§2.1–2.3, 4.1–4.3, Fig. 3 and Eq. (8). Fig. 3 and Eq. (8) also inspected visually. Online publication 2021; journal pagination 622–636, 2023. |
| [IEEE article](https://ieeexplore.ieee.org/document/9346017) / [Computer Society DOI resolver](https://doi.ieeecomputersociety.org/10.1109/TAFFC.2021.3056960) | Xplore presents JavaScript/robot verification; resolver/Computer Society access did not yield usable supplements. No protection bypass attempted. |
| Supplemental Materials I and II | Their existence and purpose are explicit in §§3.3/4.1. I contains feature statistics before/after selection; II lists task-specific eliminated participants. **Neither supplement payload was retrieved or inspected.** The exact exclusion lists remain unverified. They must not be described as absent. |
| [HAL record](https://hal.science/hal-03239520) / public HAL API and Crossref DOI metadata | HAL page access denied; API metadata points to the main IEEE paper and supplies no retrieved annex. Crossref metadata exposes no supplement relation. These checks do not prove there are no other materials. |
| Local development files and completed ablation findings | Read existing metadata and score matrices only for already inspected s1–s6 and s25. Private audit receipts include source paths, hashes, assignments and values; none enter Git. Original experiment inventories remain untouched. |

Research documents and private source snapshots are in ignored
`data/processed/ubfc-phys/label-audit/label-audit-v1/`. No third-party PDF or raw
questionnaire is redistributed in this repository. The main paper is CC BY 4.0;
this document paraphrases it with attribution and does not reproduce its forms.

## What the questionnaire measures and how it is scored

The original paper calls the forms **based on the Competitive State Anxiety
Inventory (CSAI)**, citing Martens et al., *Development and validation of the
competitive state anxiety inventory-2*, in *Competitive Anxiety in Sport* (1990).
It is not identified as STAI, perceived chronic stress, a clinical diagnosis, or
a per-frame annotation. The dataset-specific form has seven cognitive-anxiety
items, seven somatic-anxiety items and nine self-confidence items, rated 1–4.
Higher cognitive/somatic values indicate more reported anxiety; higher
self-confidence indicates more confidence, not more stress. Do not sum the three
into a fabricated stress index. [Original paper, §2.1, pp. 624–625.](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf#page=3)

Section 4.3 explicitly describes **average item scores within each dimension**,
separately before and after the session. Thus the reported mean scale is 1–4.
It also says post scores were normalized using pre scores, but does not give an
unambiguous formula there: subtraction, relative change and ratio cannot be
silently interchanged. Its group-level reliability/manipulation checks do not
establish individual diagnostic thresholds or temporal stress labels.
[Original paper, §4.3, pp. 632–634.](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf#page=11)

The exact administered item wording/language, item selection, reverse coding,
missing-item handling, and score-computation code were not obtained. A generic
CSAI-2 scoring key must not be assumed to match this adaptation. Raw item
responses are not in the inspected participant folders, so item-level scoring,
reliability and construct validity cannot be independently reconstructed.
No validated high/low stress cutoff or continuous momentary stress annotation
was found in the inspected official material. This is an evidence boundary,
not a claim that no such information exists elsewhere.

The inspected CSVs are headerless finite 3×2 matrices, within the reported mean
scale, and consistent within 0.001 with means of the stated item counts. Some
values do not follow exact three-decimal rounding; finite precision/truncation
is compatible with their representation. This is a structural consistency
check, **not proof of correct item coding**. Preserve supplied precision; do not
reverse-engineer individual answers or silently rescore the released values.
Participant values, scenario assignments and collection dates remain private.

## Administration time and correspondence

The README fixes rows to cognitive anxiety, somatic anxiety, self-confidence;
columns to **pre-experiment, post-experiment**. There is one such matrix per
participant folder, not one per task. The observed unit is a participant's one
recorded experimental session, with two occasions for each dimension. It is
not a trait-level lifelong score. [Official dataset documentation](https://ieee-dataport.org/open-access/ubfc-phys-2),
DOCUMENTATION → READ_ME.docx, “Self-reported anxiety scores”.

Pre forms were completed during the introduction, before T1. Post forms were
completed after the full T1→T2→T3 sequence, before ending discussion. The paper's
full tasks lasted 10, 6 and 4 minutes; published recordings retain only three
minutes each: middle of rest and beginning of speech/arithmetic. The end score
therefore follows more exposure than the retained clips contain. Fig. 3 and
§2.3 establish order, but no per-person questionnaire timestamp or exact
questionnaire-to-retained-frame latency is supplied in the inspected files.
[Original paper, §§2.2–2.3 and Fig. 3, pp. 625–626.](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf#page=4)

A post-session state rating is not an average over the retained clips and cannot
be attributed specifically to T2, T3, or a 30-second window. Pre-session anxiety
may already include anticipation. Exact response instructions/recall period
remain unverified without the form. Do not copy a session score onto 18 windows
and count 18 independent psychological observations. Repeated/multi-instance
modeling would still need one session outcome, participant grouping and
participant-level evaluation.

## Experimental assignment and documented label meanings

Participants were randomly assigned **once** to either `test` (harder) or `ctrl`
(easier); the assignment applies to that participant's active tasks. This is a
between-participant manipulation, not a per-window measured response or a
within-person crossover. The random sequence, allocation concealment, block/
stratification method and intended allocation ratio were not established in the
inspected description. The local metadata records assignment, not a causal effect.
[README](https://ieee-dataport.org/open-access/ubfc-phys-2) and [paper §2.2](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf#page=4).

The hard speech scenario uses a dream-job interview, removes the prepared draft,
and adds an ostensible remote expert via a fake Skype call; the easier speech
scenario concerns a positive/dream holiday. Arithmetic is spoken aloud in both
conditions, with different starting numbers and subtraction steps; errors cause
restarts. Both conditions involve interaction with a stranger. `ctrl` is not a
guaranteed unstressed state; arithmetic also includes speech. Conditions change
content, difficulty and social context together, so predicting assignment does
not isolate stress. [Paper §§2.2, 4.3.](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf#page=4)

The original paper's “non-stress/stress” analysis defines T1 as non-stress and
uses valid T2/T3 physiological features as stress (averaging them when both are
available). Its “stress level” classification uses `test`/`ctrl`. These are
**operational experimental labels**, not questionnaire-derived stress classes.
The paper reports a somatic-anxiety group difference, with other dimensions not
separating groups in that analysis. This manipulation check is not proof that
every assigned individual experienced a corresponding stress level.
[Paper §§4.2–4.3.](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf#page=8)

## What the published exclusions mean

Two separate filters must not be conflated:

1. Of 68 recruited students, 12 were not in the released 56 because of technical
   problems or refusal to share data (§2.3). A per-person reason breakdown was
   not supplied in the inspected main text.
2. Within the released dataset, §4.1 selects **paired remote/contact PRV** using
   HR agreement: PCC ≥0.40 and HR MAE ≤ceiling(task-wide mean MAE), as printed in
   Eq. (8). Initial removals were 14/33/28 in T1/T2/T3; visual inspection reinstated
   0/3/5, leaving 42/26/33 recording pairs. Supplemental II contains the list we
   could not inspect. §4.2 further requires selected T1 and at least one active
   recording for its state comparison. [Paper §§2.3, 4.1–4.2.](https://lead.ube.fr/wp-content/uploads/2025/04/Meziati_Sabour_et_al._2023.pdf#page=7)

The second filter is agreement-based selection of both modalities, with manual
exceptions. It does not independently identify a bad wrist reference versus a
bad camera signal, certify video decoding/face quality, or label stress. Do not
import those exclusions as our camera eligibility policy or choose regions by
reference agreement. The task-dependent selection also limits portability of
published performance figures. Our frozen camera policies and full scheduled
inventory remain in effect; synchronization is still unverified locally, so
camera/wrist comparisons remain at recording level.

## Feasible targets and units

| Target | Statistical observation / grouping | What is defensible | What it cannot establish |
|---|---|---|---|
| Rest vs speech; separately rest vs arithmetic | Original window predicts task; windows clustered within task/session/person. Participant-held-out fitting and participant-level uncertainty. | Existing exploratory task discrimination and extraction/quality engineering. | A psychological state, response severity, or independence of windows. Behaviour/order/conditions can identify task. |
| Questionnaire outcome prediction | One participant-session row with paired pre/post values; one outcome per dimension, not per window. All sessions of a person share a split. | Continuous post-session state-anxiety or prespecified pre/post change association with camera summaries, after scoring clarification. | Momentary stress, causality, task-specific anxiety, or a generic psychological stress diagnosis. Self-report is an imperfect criterion. |
| `test` vs `ctrl` classification | One assigned participant-session; if tasks are modeled separately, repeated task rows still cluster by person. | Recognition of assigned difficulty/social-evaluation package; within-task comparisons can reduce the rest-vs-active difference. | Individual measured stress intensity or removal of content/difficulty/behaviour confounding. Assignment is not an app input. |

Completed development ablations found that removing both mouth and motion
families left no consistent advantage over nuisance controls. This motivates
construct validation, not selection of a new winning model or rebranding task
accuracy as stress accuracy. Numerical findings remain in the private completed
review; no models or feature tables were changed in this audit.

## Recommendation and mentor questions

Keep the engineering deliverable honest: a camera feature/quality pipeline with
exploratory task classification. If the project needs a psychological outcome,
propose **session-level cognitive-anxiety change**, defined as released post mean
minus released pre mean, in original score units. This subtraction is our explicit
future estimand, not a recovered formula from the paper. Keep somatic change and
self-confidence change separate secondary outcomes. Do not choose somatic anxiety
as primary solely because the original paper found a group difference.

This endpoint uses recordings from the same session to estimate a subsequent
self-report; it is not prospective pre-session prediction or passive real-time
monitoring. Availability does not imply that seven development participants can
support a useful model. The [untouched-participant draft](untouched-evaluation.md)
locks comparisons and preprocessing but has unresolved cohort/measurement gates.

Mentor input is needed on:

- Whether session anxiety is an acceptable narrowing of “mental-stress detection”,
  or momentary stress is a required deliverable.
- Obtaining the exact administered form/scoring instructions and the two official
  supplements through legitimate institutional/author access; clarifying item
  adaptation, missing-item/reverse coding, and pre-normalization formula. No
  message was sent to authors or anyone else.
- The construct and primary dimension, acceptable error/precision, independent
  participant count and population, and whether protocol-dependent session
  features match the intended webcam use. These must be settled before new data
  or training, not after selecting favorable outcomes.
- For a real momentary-stress study: ethics/consent and a design with time-local
  validated ratings at prespecified block boundaries, recorded questionnaire/event
  timestamps and response lags, repeated low/high-demand blocks matched for
  speaking/movement, recovery, counterbalanced/randomized conditions where
  feasible, and multiple sessions/independent participants. Keep psychological
  ratings, manipulation assignment and physiological checks distinct; wrist data
  are corroboration, not an oracle. Labels must have a justified temporal
  resolution, not be interpolated into 30-second ground truth without validation.

New participants test transfer between people; they cannot by themselves break
an unchanged association between task, behaviour, order and stress induction.
The next concrete step is to resolve the form/target gates and finalize the
session-level evaluation preregistration. No further fitting or acquisition is
authorized by this document.
