# Focused literature review

Checked 2026-11-08. This is a targeted comparison, not a systematic review or
proof of novelty. Earlier titles, performance numbers, and novelty claims were
not accepted as evidence. Search results were used to locate sources only.
Technical entries below come from inspected primary full texts or explicitly
identified publisher previews. Unknown means unverified, not absent.

## Comparison

| Verified publication and source | Inputs / dataset | Prediction target and labels | Split / leakage controls | Metrics and protocol | Quality, fusion, rejection | Code / relevance |
| --- | --- | --- | --- | --- | --- | --- |
| **Multimodal Deep Learning for Remote Stress Estimation Using CCT-LSTM** — Sayyedjavad Ziaratnia, Tipporn Laohakangvalvit, Midori Sugaya, Peeraya Sripian; WACV 2024. [Official full PDF](https://openaccess.thecvf.com/content/WACV2024/papers/Ziaratnia_Multimodal_Deep_Learning_for_Remote_Stress_Estimation_Using_CCT-LSTM_WACV_2024_paper.pdf). | Facial landmarks + camera-derived rPPG; UBFC-Phys. | Task discrimination, including T1/T2/T3. Separate experiment: T1 versus T3-ctrl versus T3-test; difficulty groups are not measured stress severity. | Seven participant folds for task experiment; five stratified participant subsets for second experiment. Separate calibration/model-selection partition not clearly specified; PCA fit scope not fully established. | 60-second windows, 5-second step; accuracy and F1 with fold variability, Table 1 binary and three-class tasks. | CCT/LSTM fusion; Face2PPG region selection addresses noisy regions. No explicit prediction-abstention or matched-coverage confidence comparison identified. | No implementation link found in inspected PDF. **Direct modality/dataset competitor**; combining face and rPPG is already established. |
| **Multimodal Stress State Detection from Facial Videos Using Physiological Signals and Facial Features** — Yassine Ouzar, Lynda Lagha, Frédéric Bousefsaf, Choubeila Maaoui; 2023 publication of ICPR 2022 workshop. [Publisher](https://link.springer.com/chapter/10.1007/978-3-031-37745-7_10), DOI `10.1007/978-3-031-37745-7_10`. | Facial features + remote PRV; single-camera input, UBFC-Phys. | Publisher calls target stress state; exact mapping of tasks/groups unavailable in preview. | Unknown: subscription full text inaccessible; do not infer participant independence. | Preview reports accuracy but insufficient protocol detail for comparison; number deliberately not used as a benchmark. | Multimodal fusion confirmed by abstract; quality thresholds, fusion implementation and rejection unknown. | No author implementation verified. Closest earlier face/remote-physiology fusion; full-text verification remains a priority. |
| **Quality-Aware Multimodal Stress Recognition with QA-Soft Fusion and Adaptive Windows** — Murat Kunelbayev, Gulnur Tyulepberdinova, Gulshat Amirkhanova, Madiyar Zauranbek, Octavian Postolache; 2026. [Publisher full PDF](https://www.etasr.com/index.php/ETASR/article/download/19489/7161/106743), DOI `10.48084/etasr.19489`. | Wearable PPG/HRV, EDA, temperature, IMU; 16-person pilot; WESAD extension. | Protocol rest=0, speech/counting induction=1, physical activity=2; not clinical diagnoses. | Reports LOSO/Group K-Fold. Detailed fold assignments and nesting of subject/session normalization, calibration and threshold fitting not fully reproducible from inspected text. | Macro-F1, PR/ROC-AUC, physical-activity false alarms, Brier/ECE; participant comparisons. Tables X–XII report rejected windows and fixed coverage. | SQI/motion-dependent soft fusion; uncertain windows suppress alarms; adaptive windows. No matched-coverage confidence-only comparator established in inspected sections. | No code link identified; pilot data on request. **Direct conceptual competitor**: quality-aware stress fusion and rejection are not new in general. |
| **Trusted Multi-View Classification** — Zongbo Han, Changqing Zhang, Huazhu Fu, Joey Tianyi Zhou; ICLR 2021. [Author manuscript](https://arxiv.org/html/2102.02051), [conference record](https://openreview.net/forum?id=OOsR8BzCnl5). | Multiple feature views; Handwritten, CUB, PIE, Caltech101, Scene15, HMDB. | Dataset category labels, not stress outcomes. | Appendix A.6: 20% sample test set, five-fold learning-rate selection, 30 runs; participant-separated stress evaluation not applicable or demonstrated. | Accuracy/AUROC; noise experiments and accuracy under uncertainty thresholding. | Dirichlet evidence, Dempster–Shafer fusion; uncertainty-based view reliability. Gaussian feature corruption differs from video degradation. | [Author code](https://github.com/Han-Zongbo/TMC) verified, not run. Established uncertainty-fusion comparator; does not establish physiological validity or deployment risk guarantees. |
| **Selective Classification for Deep Neural Networks** — Yonatan Geifman, Ran El-Yaniv; NeurIPS 2017. [Official full PDF](https://proceedings.neurips.cc/paper/7073-selective-classification-for-deep-neural-networks.pdf). | Image classifiers; CIFAR-10/100, ImageNet. | Image categories; selective 0/1 classification error. | Threshold-selection analysis assumes independent identically distributed labeled samples; participant-grouped video windows are not its demonstrated setting. | Risk–coverage trade-off; finite-sample risk control under stated assumptions. | Post-hoc softmax-response and MC-dropout selection; no measured-video-quality fusion. | Standalone author implementation not verified here. Foundational confidence-only rejection baseline; its guarantees cannot simply be transferred to shifted/correlated video windows. |
| **SelectiveNet: A Deep Neural Network with an Integrated Reject Option** — Yonatan Geifman, Ran El-Yaniv; ICML 2019. [Publisher](https://proceedings.mlr.press/v97/geifman19a.html), [full PDF](https://proceedings.mlr.press/v97/geifman19a/geifman19a.pdf). | SVHN, CIFAR-10, Cats vs. Dogs; concrete-strength tabular regression. | Image categories / compressive strength, not stress. | Benchmark sample train/test partitions; independent unlabeled validation proposed for coverage calibration (§5). No participant stress split. | Selective classification error or regression loss at specified coverage; comparison with softmax response and MC-dropout. | Joint prediction/selection/auxiliary heads; coverage-constrained loss. | [Author code](https://github.com/geifmany/SelectiveNet) verified, not run. Learned abstention is established; useful later comparator, not a reason to start deep training now. |
| **A hybrid deep temporal architecture for multimodal stress prediction** — Yogesh J. Gaikwad, N. Mohankumar, Gagandeep Kaur; 2026. [Full publisher article](https://link.springer.com/article/10.1007/s10791-026-10719-4), DOI `10.1007/s10791-026-10719-4`. | Facial features + **contact** BVP/EDA, UBFC-Phys; not camera-only pulse. | Continuous stress regression; exact construction of target not established sufficiently in the inspected methods to reproduce it. Do not adopt its target by assumption. | Reports 45 development / 11 fixed test participants and development five-fold GroupKFold; train-fitted learned transformations. | MAE/RMSE/R²; final subject-independent evaluation reports negative R² and limits its claims. Earlier sequence-level analyses explicitly not confirmatory. | PCA/concatenation, BiLSTM, optimized XGBoost; no verified selective-rejection comparison. | No code link found. Adjacent multimodal comparator and caution about subject shift; numerical regression results are not comparable to task accuracy. |
| **UBFC-Phys: A Multimodal Database For Psychophysiological Studies Of Social Stress** — Rita Meziati Sabour, Yannick Benezeth, Pierre De Oliveira, Julien Chappé, Fan Yang; online 2021, journal issue 2023. [Official author page](https://sites.google.com/view/ybenezeth/ubfc-phys), DOI `10.1109/TAFFC.2021.3056960`. | Camera video, wrist BVP/EDA, pre/post self-report; UBFC-Phys. | Three experimental tasks; session-level self-report distinct from conditions. See dataset documentation. | Original evaluation split, exclusions and selection effects **not fully verified** in this task. | Earlier conversational accuracy figures are not adopted here. | Full algorithm/evaluation details unknown without complete accessible paper and supplements. | [Xplore](https://ieeexplore.ieee.org/document/9346017) requires browser verification; author-linked Drive download returned HTML. No author code verified. Dataset source, not evidence of our model's performance. |

## Evidence boundaries and consequences

The CCT-LSTM PDF was downloaded from CVF and read locally; web-reader HTTP 403
did not prevent this. Relevant locations are §§3–4.4 and Table 1. Its binary task
comparisons already cover rest/speech and rest/arithmetic. These tasks remain
useful **controlled evaluation targets**, rather than a novel label design.

QA-Soft was read in the publisher PDF, especially §§II–III and IV.F, Tables
X–XII. It already examines coverage and rejected windows. Broad claims of being
the first quality-aware stress-fusion or abstention system are therefore
unsuitable. Our narrower comparator and camera degradation design are an
experimental proposal; absence from this focused review is not proof of novelty.

**Our inference about UBFC-Phys:** talking, mouth/head motion, task order and
camera artifacts can co-vary with T1/T2/T3. A task classifier can exploit those
differences without detecting a participant's psychological response. Separating
two binary contrasts, measuring nuisance-only performance, and reporting
class-conditional coverage help audit this problem but cannot eliminate it.
Neither a correct pulse estimate nor a high task-classification score validates
psychological stress. The session questionnaire does not supply window-level
ground truth. This reasoning follows the experimental design documented in
[dataset access](dataset-access.md); it is not a new empirical finding.

No cross-paper accuracy ranking is provided. Different targets, cohorts,
exclusions, window overlap, learned preprocessing, and participant partitions
make raw percentages noninterchangeable. Within-paper ablations are useful only
under their stated protocol. Code availability is not code validation.

## Remaining evidence work

- Obtain legitimate browser/institutional access to the original UBFC-Phys paper
  and supplements, and the Ouzar chapter. Confirm exact task instructions,
  retained-segment timing, subject exclusions, and participant grouping. Use the
  official URLs above; do not infer unavailable methods from abstracts.
- A secondary reference trail named a Du/Yang SPIE 2025 work on remote mental
  stress assessment. Its primary record/full text was not verified, so it is
  **excluded from the comparison and from technical/novelty evidence**. Verify
  this lead before any novelty assertion; no title, DOI or performance figure
  from that trail is treated as established.
- Check whether direct competitors provide confidence-only versus measured
  quality comparisons at genuinely matched coverage, with independent
  participants and controlled image corruption. Expand author-repository and
  recent conference searches before publication. Current evidence is incomplete.
- Calibration and group-aware uncertainty procedures need implementation review
  before analysis; selective guarantees under an IID model do not establish
  guarantees for dependent windows or degradation shift.

Public papers used for reading remain outside the repository. No third-party
PDFs, participant information, or experimental outputs are included. The
[provisional protocol](research-protocol.md) states what will be tested, not what
has already been demonstrated.
