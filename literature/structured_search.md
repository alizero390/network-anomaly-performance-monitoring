# Structured literature search for Paper 1

Second pass, 2026-11-10, building on `scoping_review.md`. Purpose: test whether Paper 1's
claims are already published, and collect the work it must cite.

## Protocol

**Questions.** For each Paper 1 claim (see `results/paper1_status_and_claims.xlsx`):
has it been shown before, for network intrusion detection or for monitoring in general?

**Sources.** Open web search engine with Google-Scholar-style queries, arXiv, publisher
pages. No subscription databases (Scopus, IEEE Xplore, ACM DL) were used, so recall is
lower than a database search; repeating the queries there remains a pre-submission task.

**Inclusion.** Peer-reviewed papers or preprints that (a) evaluate intrusion detection
metrics under class imbalance or prevalence change, (b) monitor deployed model
performance or drift, with or without delayed labels, (c) analyse UNSW-NB15 or CIC-IDS-2017
evaluation practice, or (d) study the prevalence dependence of classification metrics.

**Exclusion.** Vendor blogs and tutorials; patents; papers proposing a new detector with
no bearing on evaluation or monitoring; pages that could not be opened.

**Screening.** Titles and snippets screened from each query; candidates opened and read
(abstract plus the relevant sections). A paper counts as read only if its page was opened.
All queries, with counts, are in `search_log.md`.

## Included studies (this pass)

| Key | Study | What it shows | Relevance to Paper 1 |
|---|---|---|---|
| guesne2024prevalence | Guesné et al., *J. Cheminformatics* 2024, ["Mind your prevalence!"](https://link.springer.com/article/10.1186/s13321-024-00837-w) | MCC and accuracy depend on test-set prevalence and can move opposite to sensitivity and specificity; balanced accuracy does not | General basis for claim 1; recommends balanced metrics, which claim 4 qualifies |
| siblini2020calibration | Siblini et al., ["Master your Metrics with Calibration"](https://arxiv.org/abs/1909.02827) | Precision and F1 vary with the class ratio; a calibrated precision/F1 rescales to a reference ratio | Existing remedy for claim 1; a candidate baseline metric to test |
| thiyagarajan2025mcc | Thiyagarajan and Williams, arXiv 2512.19203 ([link](https://arxiv.org/abs/2512.19203)) | For rare attacks in CIC-IDS-2017 subsets, MCC is more informative than accuracy | Static cross-validation only; no time windows, alarms or changing prevalence |
| jin2026benchmarkshift | Jin and Lee, *Electronics* 15(17):3761, 2026 ([link](https://www.mdpi.com/2079-9292/15/17/3761)) | Cross-dataset and day-level CIC-IDS-2017 shift; source thresholds fail; recommends SOC drift monitoring with delayed labels | Closest recent NIDS work; monitoring is recommended, not tested; no windowed alarms |
| parlanti2025temporal | Parlanti and Catania, arXiv 2511.03799 ([link](https://arxiv.org/abs/2511.03799)) | Taxonomy of time-aware NIDS; calls for temporal metrics | No deployed-performance monitoring, label delay or prevalence change |
| poenaru2022drift | Poenaru-Olaru et al., arXiv 2211.13098 ([link](https://arxiv.org/abs/2211.13098)) | Drift detectors are unreliable alarm systems; high false-positive rates; class imbalance raises misses | Supports the alarm-quality framing; no NIDS data, no prevalence change |
| oda2026whatchanged | Oda, arXiv 2609.27865 ([link](https://arxiv.org/abs/2609.27865)) | Separates real from virtual drift; error-stream detectors fire on pure covariate shift; delayed labels slow real-drift detection by the delay | Same spirit as "harmless vs harmful shift"; label shift not studied; no NIDS data |
| xu2020lagged | Xu and Klabjan 2020 ([PDF](https://www.mccormick.northwestern.edu/research/deep-learning/documents/publications/drift_detection.pdf)) | Ensemble of label-based and label-free drift signals under lagged labels | Precedent for Strategy C; no NIDS data |
| zoghi2024overlap | Zoghi and Serpen, *Concurrency and Computation: Practice and Experience* 36:e8242, 2024 ([DOI](https://doi.org/10.1002/cpe.8242); open access) | Ensemble with threshold adjustment for class overlap and imbalance; Fuzzers, Backdoor and Normal overlap; attack types that mimic normal traffic (Fuzzers, Analysis, Shellcode) are confused with Normal; multi-class Fuzzers sensitivity 72.25% | Uses the official randomly partitioned training/testing sets (175,341 / 82,332) with stratified random validation: no temporal split, windows or monitoring. Dataset-level support for claim 5; confirms the temporal angle is not covered |
| botacin2024labeldelays | Botacin and Gomes, *Computers & Security* 2024 ([author's copy](https://marcusbotacin.github.io/files/label-delays.pdf)) | Label delays from analyst/sandbox queues delay drift-triggered retraining; an 81-epoch delay raises exposure (accumulated false negatives) by about 50% | Direct precedent for RQ4 (label delay); malware, not NIDS; proposes a time-aware 'exposure' metric |
| hindy2020zeroday | Hindy et al. 2020, arXiv 2006.15344 ([link](https://arxiv.org/abs/2006.15344)) | Autoencoder trained on benign traffic detects unseen CIC-IDS-2017 attacks at 75-98% | Context for the CIC-IDS-2017 unseen-attack result (different set-up: one-class) |

**Added 2026-11-12** (site-restricted web searches standing in for IEEE Xplore and eLibrary; see `search_log.md`):

| Key | Study | What it shows | Relevance |
|---|---|---|---|
| cai2023disde | Cai, Namkoong and Yadlowsky, "Diagnosing Model Performance Under Distribution Shift", arXiv 2303.02011 ([link](https://arxiv.org/abs/2303.02011)) | Splits a performance drop under shift into harder-but-seen examples, changed feature-outcome relation and unseen examples | Method-level precedent for decomposing a drop (Paper 1 F1 decomposition; thesis harmful vs harmless shift); no NIDS data, no windows or alarms |
| wang2021robustness | Wang and Machida, "A Robustness Evaluation of Concept Drift Detectors against Unreliable Data Streams" (IEEE; [author copy](https://www.cs.tsukuba.ac.jp/~machida/wfiot2021-wang.pdf)) | Six drift detectors on a synthetic stream: wrong labels hurt delay and precision far more than missing labels; CUSUM most robust | Precedent for the thesis's partial-label condition; synthetic data, no label delay, no NIDS |
| cantone2024crossdataset | Cantone, Marrocco and Bria, *J. Information Security and Applications* 2024 (arXiv [2402.10974](https://arxiv.org/abs/2402.10974)) | Near-perfect within-dataset NIDS results collapse across datasets; reports MCC and F1, drops accuracy for imbalance | Random 80:20 splits, no time windows: supports that temporal evaluation is missing; cite with Jin and Lee |
| apruzzese2023pragmatic | Apruzzese, Laskov and Schneider, "SoK: Pragmatic Assessment of Machine Learning for Network Intrusion Detection", IEEE EuroS&P 2023 (arXiv [2305.00550](https://arxiv.org/abs/2305.00550)) | Benchmark-driven NIDS research ignores deployment factors; proposes "pragmatic assessment" | Context for the deployment framing; the abstract does not cover monitoring or labels |
| ackerman2020drift | Ackerman et al. (IBM Research), "Detection of Data Drift and Outliers Affecting Machine Learning Model Performance Over Time", arXiv 2012.09258 ([link](https://arxiv.org/abs/2012.09258)) | Label-free drift detection from the model's confidence distribution, with change-point models that hold the false-alarm rate fixed | Candidate label-free signal for a Strategy A ablation; covers prior-probability shift; no NIDS |
| biswas2026protocol | Biswas, "The Evaluation Protocol Is the Hidden Variable: A Drift-Aware Re-Examination of Flow-Based Intrusion Detection Benchmarks", Preprints.org 202606.0903, June 2026, not peer-reviewed ([link](https://www.preprints.org/manuscript/202606.0903)) | CSE-CIC-IDS2018: macro-F1 about 0.79-0.82 with random splits, about 0.02 with a chronological split; cross-dataset transfer below chance | Strong support for time-ordered evaluation; offline only, no windowed monitoring or alarms; cite as a preprint |
| protic2023datasets | Protić and Stanković, *Vojnotehnički glasnik* 71(4), 2023 ([CyberLeninka](https://cyberleninka.ru/article/n/cybersecurity-attacks-which-dataset-should-be-used-to-evaluate-an-intrusion-detection-system)) | Review of IDS datasets including UNSW-NB15 and CIC-IDS-2017 | Context only; no metrics, imbalance or drift analysis |

Not opened: "A Change Detector for Prior Probabilities of Classes" (IEEE SSCI 2020): every copy found was blocked. Worth a look in IEEE Xplore when the database search is run.

The Russian-language site-restricted searches found no study on monitoring deployed detectors or on metric behaviour under changing prevalence. The novelty assessment below is unchanged.

**IEEE Xplore database search, 2026-11-12** (684 records, 9 included; screening in `search_log.md`):

| Key | Study | What it shows | Relevance to Paper 1 |
|---|---|---|---|
| dasgupta2026drift | Dasgupta, Biswas and Kar, "Evaluation of Intrusion Detection Systems Under Concept Drift and Severe Class Imbalance", ICC-CNS 2026, doi 10.1109/ICC-CNS70518.2026.11606116 | UNSW-NB15 streaming evaluation over 36 rolling windows with controlled synthetic drift; accuracy hides failure (2.14 vs 39.77 percentage-point gap under balanced accuracy); static Random Forest does not recover after drift; recommends balanced accuracy, per-class recall and FPR | **Closest study found.** Windowed UNSW-NB15 metrics, but synthetic drift, no changing attack prevalence, no alarm rule or alarm evaluation, no label delay. Claim 4 qualifies its balanced-accuracy recommendation; it supports reporting per-class recall and FPR. Must be cited and positioned |
| doynov2026lowbase | Doynov, Nenova and Manolova, "Recall-First Temporal Routing for Low-Base-Rate IDS ...", ECTI DAMT & NCON 2026, doi 10.1109/ECTIDAMTNCON67592.2026.11460005 | Multi-window protocol that selects low-base-rate windows: recall 0.9997 overall, but worst-case FPR 1.0 and 100% alert rate in low-base windows | Independent evidence that aggregate metrics hide behaviour in low-attack windows (claim 1 context); no monitoring alarms |
| katiyar2026health | Katiyar and Silva, "Early Detection of Classifier Health Deterioration Under Zero-Day Cyberattacks", ICNCCom 2026, doi 10.1109/ICNCCom69117.2026.11736219 | Label-free health index from SVM margins on CIC-IDS2017 with unseen attacks added; beats KS, Page-Hinkley and cluster distance; flags deterioration while macro-F1 stays above 97% | Label-free monitoring compared with KS: relevant to Strategy A and the thesis; Paper 1 context (F1 as a monitoring signal) |
| ghausi2026leakage | Ghausi et al., "Poster: Rethinking Intrusion Detection Evaluation: The Impact of Cross-Scenario Leakage", SVCC 2026, doi 10.1109/SVCC69905.2026.11642257 | CIC-IDS2017 day-based holdout: attack recall drops sharply though ROC-AUC and PR-AUC stay high; notes holdout changes attack-family composition and class ratios | Supports the day-split CIC-IDS-2017 design and claim 5 (attack mix) |
| khan2026leakage | Khan, "Leakage-Aware IDS Evaluation under Unseen Attacks and Cross-Dataset Shift", IAICT 2026, doi 10.1109/IAICT71158.2026.11620817 | CIC-IDS2017 and UNSW-NB15: F1 0.994/0.959 in-domain, sharp drop for unseen PortScan and cross-dataset transfer | Supports the unseen-attack CIC result |
| zhang2026tgnnaudit | Zhang et al., "Are Temporal Graph Based Intrusion Detection Results Trustworthy? A Dataset Audit and Evaluation Framework", IMNS 2026, doi 10.1109/IMNS67862.2026.11655312 | Names temporal concentration of attack traffic as a dataset flaw; proposes an attack-aware chronological split | Matches the January finding (all attacks in 2 hours) and our attack-period split |
| bernardo2025driftgen | Bernardo, Faria and Miani, "Drift Dataset Generator for Evaluating Flow-Based Intrusion Detection Systems", IEEE CCNC 2025, doi 10.1109/CCNC54725.2025.10976194 | Injects controlled drifts into public IDS datasets (case study on CIC-IDS2017) | Alternative to the thesis scenario construction (design spec D3); cite there |
| shukla2025ddos | Shukla et al., "Efficient DDoS Detection Under Distribution Shift ...", ACET 2025, doi 10.1109/ACET67282.2025.11430287 | CIC-DDoS2019: chronological vs random splits, window summaries | Context for time-ordered evaluation |
| qiu2025streaming | Qiu and Heywood, "Benchmarking Streaming Evolutionary Ensemble Learning under Shifting Imbalanced Data", IEEE CEC 2025, doi 10.1109/CEC65147.2025.11043023 | Streaming botnet benchmark with shifting class imbalance; prequential metrics | Context only |

**Effect on the novelty assessment.** Dasgupta et al. (2026) is now the closest work: it
evaluates detectors in windows on UNSW-NB15 under drift and imbalance. It still differs on
every point Paper 1 claims: drift is injected synthetically, the attack share does not
change on its own, no alarm rule is applied or evaluated, and it recommends balanced
accuracy, which claim 4 qualifies. IEEE Q1 returned no paper at all on intrusion
detection with delayed labels, which supports the thesis gap (RQ4).

**OpenAlex search (stand-in for Scopus), 2026-11-12** (1,029 unique records, 12 included; screening in `search_log.md`). Peer-review status is given because several records are preprints.

| Key | Study | What it shows | Relevance |
|---|---|---|---|
| ahmed2026dashboard | Ahmed, Rahaman, Roy, Alam, "The dashboard says 'perfect': a systematic audit of label-free model monitoring and test-time adaptation under temporal distribution shift in network intrusion detection", *Frontiers in AI* 2026, doi 10.3389/frai.2026.1928858 (peer-reviewed) | CIC-IDS2017 to CSE-CIC-IDS2018 one year later: label-free monitors give predicted accuracy 1.000 to a model whose recall on every attack family is 0; label-free selectors pick the wrong model in 10-12 of 12 trials; only the conformal abstention rate behaves correctly | **Key for the thesis**: label-free proxies (Strategy A-type signals) can certify a blind detector as healthy, so label-based confirmation (Strategy B) is needed. Paper 1 discussion: monitoring needs labels and trustworthy metrics |
| li2026alertbudget | Li and Zhou, "From Risk Scores to Budget-Constrained Alert Streams: Temporal Evaluation of Flow-Level Network Intrusion Detection", *Electronics* 15(20):4854, 2026, doi 10.3390/electronics15204854 (peer-reviewed) | Forward-time replays on CICIDS2017, UNSW-NB15 and NF-ToN-IoT-v3: historical thresholds overrun false-positive budgets; reports alert load at an assumed attack prevalence; UNSW-NB15 diagnosis changes with the capture-session split | Close in spirit (time order, operational alert load, prevalence); no windowed degradation alarms. Supports reporting FPR separately (claims 1 and 4) and the session effect we saw (February vs January) |
| youssef2026stream | Youssef, "Stream Assembly Is an Uncontrolled Treatment in Streaming Intrusion-Detection Benchmarks", arXiv 2605.24696, 2026 (preprint) | How evaluation streams are assembled changes test prevalence (CICIDS2017: 68.2% vs 25.2%) and can reverse which detector looks better | Supports claim 1 (prevalence changes measured results) and the design spec D3: stream construction must be controlled and reported |
| nagtegaal2026imbalance | Nagtegaal and Oosterbeek, "Disentangling class imbalance from feature drift as causes of intrusion detector degradation: A controlled ablation", *Int. J. Communication and Information Technology* 7(3), 2026, doi 10.33545/2707661x.2026.v7.i3a.222 (low-visibility journal) | Random Forest F1 0.96 to 0.58 from 1:100 imbalance alone, vs 0.64 from high feature drift | Supports that imbalance alone moves F1 (claim 1); static ablation, not windowed monitoring. Cite with care |
| kumar2026foursins | Kumar, "Four Sins of Intrusion-Detection Evaluation: Quantifying the Reported-to-Deployed Performance Gap with a Shapley Decomposition", Zenodo, 2026, doi 10.5281/zenodo.21454035 (not peer-reviewed; synthetic data) | Base-rate fallacy, temporal leakage, closed-world testing and threshold snooping decomposed as factors of the reported-to-deployed gap | Base-rate effect named as a known evaluation sin; synthetic only. Context for claim 1 |
| bakhtiar2026floors | Bakhtiar, "Prospective Worst-Attack Reliability Floors for Flow-Based Machine-Learning Intrusion Detection under Forward-Time Shift", *AVITEC* 9(1), 2026, doi 10.28989/avitec.v9i1.4296 | UNSW-NB15 forward-time test: 95.9% accuracy but 68.1% balanced accuracy; worst attack-family recall 22%; Analysis, Backdoor, Reconnaissance fail their floors | Supports claim 5 (attack families drive recall) and per-family reporting on UNSW-NB15 |
| alalawi2026calibration | Alalawi, "When Calibrated Detectors Meet New Attacks: Per-Category Reliability ...", *IJACSA* 17(8), 2026, doi 10.14569/ijacsa.2026.0170812 | Calibration holds on UNSW-NB15's official split (same categories) but fails on NSL-KDD's unseen attacks | Context for unseen-attack results (CIC Botnet) |
| vo2026longterm | Vo and Truong, "Evaluating Long-Term Performance of ML-based Intrusion Detection Systems under Temporal and Structural Changes", 2026, doi 10.65153/bw356376 (regional journal) | Chronological train/test separation on CIC-IDS2017 and CSE-CIC-IDS2018; tree models overfit under temporal shift | Context for time-ordered evaluation |
| pall2026trustshift | Pall, "TrustShift: Shift Type, Not Shift Magnitude, Determines Machine-Learning Failure Modes", Zenodo, 2026, doi 10.5281/zenodo.21805027 (not peer-reviewed) | Across four domains incl. CIC-DDoS2019 to CICIDS2017: shift magnitude does not predict damage; covariate shift alone broke nothing, novel-label shift blinded the detector | Thesis framing (harmless vs harmful shift; Strategy A detects magnitude, not harm) |
| jeon2026labelefficient | Jeon and Kim, "A Label-Efficient Adaptive Retraining Framework for Network Intrusion Detection Under Streaming Arrival Bias", *Electronics* 15(17):3812, 2026, doi 10.3390/electronics15173812 (peer-reviewed) | Degradation severity cannot be inferred from distributional change; labels drawn from the first hours fail ("arrival bias") | Thesis: supports label-based confirmation and the partial/biased-label conditions (design spec D7) |
| palli2022driftimbalance | Palli et al., "An Experimental Analysis of Drift Detection Methods on Multi-Class Imbalanced Data Streams", *Applied Sciences* 12(22):11688, 2022, doi 10.3390/app122211688 (peer-reviewed) | Class imbalance raises the false-alarm rate of most drift detectors | General support for claim 1 (imbalance and false alarms); not NIDS |
| dasgupta2026ssrn | Dasgupta, "When Drift Injection and Drift Detection Disagree: Re-evaluating Phase-Based Drift Analysis for Network Intrusion Detection Models", SSRN, 2026, doi 10.2139/ssrn.7604719 (preprint; no abstract available) | Follow-up to dasgupta2026drift | Read before submission |

**Effect on the novelty assessment (OpenAlex).** Several 2026 studies evaluate NIDS in
time order or name the base rate as a source of misleading results (Li and Zhou;
Youssef; Kumar). None applies a windowed degradation-alarm rule, measures false-alarm
rates under pure attack-share change, attributes alarms to causes, or tests calibrated
F1. Paper 1's claims stand, but the related-work section must acknowledge that the
prevalence problem is increasingly recognised in 2026, and position Paper 1 as the
monitoring-alarm study. For the thesis, Ahmed et al. (2026) is strong motivation:
label-free monitors certified a blind detector as perfect.

**Russian-language studies** (needed for a Russian journal):

| Key | Study | What it shows | Relevance to Paper 1 |
|---|---|---|---|
| namiot2022shift | Намиот Д.Е., Ильюшин Е.А. Мониторинг сдвига данных в моделях машинного обучения // International Journal of Open Information Technologies. 2022. Т. 10, № 12. С. 84-93 ([PDF](https://injoit.ru/index.php/j1/article/download/1462/1350)) | Survey of label-free shift detection (KS, chi-square, PSI, DDM) and a monitoring architecture | Russian-language basis for Strategy A |
| kotenko2024attacks | Котенко И.В. и др. Атаки и методы защиты в системах машинного обучения // Вопросы кибербезопасности. 2024. № 1(59). С. 24-37. DOI 10.21681/2311-3456-2024-1-24-37 ([PDF](https://cyberrus.info/wp-content/uploads/2024/02/vokib-2024-1-st03-s024-037.pdf)) | Review of adversarial attacks and defences for ML | Context only; shows that journal publishes in Russian with English abstracts |
| pokidko2025transfer | Покидько А.Ю., Степанов И.А., Гетьман А.И. Перенос обучения в сетевых системах обнаружения вторжений: обзор методов и подходов // Труды ИСП РАН. 2025. Т. 37, № 6. С. 73-90. DOI 10.15514/ISPRAS-2025-37(6)-37 ([link](https://ispranproceedings.elpub.ru/jour/article/view/2085/1907)) | Review of transfer learning for NIDS, framed around drift of network data and new attack types | Russian-language source on drift in NIDS; published in the fallback journal (Труды ИСП РАН). Adaptation, not monitoring |
| bashmakova2024botnet | Башмакова Н.М. и др. Обнаружение сетевых атак ботнетов на основе технологий машинного обучения и переноса знаний // Информационно-управляющие системы. 2024. № 5. С. 41-56. DOI 10.31799/1684-8853-2024-5-41-56 ([PDF](https://i-us.ru/index.php/ius/article/download/16320/15374)) | ML botnet detection with transfer between datasets; names concept drift as an open problem | Russian-language context for the unseen-Botnet result |

Included earlier (`scoping_review.md`): Zoghi and Serpen; Flood et al.; Arp et al.;
INSOMNIA (Andresini et al.); Fernández-Barrios et al.; Luay et al.; Rabanser et al.;
Garg et al.; Białek et al.; Lipton et al.; Žliobaitė; Solozobov; Engelen et al.; Liu et al.

## Novelty assessment by claim

| # | Claim | Already known | What appears new | Risk |
|---|---|---|---|---|
| 1 | F1/MCC raise false degradation alarms when attacks become rare | Prevalence dependence of F1, precision and MCC (Guesné; Siblini) | Quantified as alarm rates of a windowed monitoring rule on NIDS models, and shown to scale with the model's FPR across 6 runs and 2 datasets | Medium: the mechanism is known, so the paper must lead with the monitoring consequence and the FPR dependence |
| 2 | A reference from the first monitored windows can hide real failures | Reference/window choice is discussed for drift detectors in general | Shown on real NIDS traffic: CIC-IDS-2017 Friday reference = 0 or undefined, no alarm during total Botnet failure; February UNSW-NB15 first alarm at window 57 vs 2 | Low (none found) |
| 3 | F1/MCC add harmless alarms that recall does not | Indirectly implied by prevalence dependence | Alarm attribution by cause on real windows | Low (none found) |
| 4 | Balanced accuracy hides false-positive bursts | Balanced accuracy is recommended as prevalence-independent (Guesné) | Counter-evidence for monitoring: January UNSW-NB15 FPR bursts (4-9%) that F1 flags and balanced accuracy barely registers | Low; directly qualifies a published recommendation |
| 5 | Attack-type mix explains window recall | Generic dominance and Fuzzers' difficulty at dataset level (Zoghi and Serpen; Flood) | Temporal: category mix explains R² 0.31-0.76 of window recall across 6 runs | Low-medium: cite the dataset-level work |

**Overall** (updated 2026-11-12 after the IEEE Xplore search). No paper found combines windowed performance monitoring of NIDS models, attack
prevalence that changes over time, alarm-level evaluation and attribution of alarms to
causes. The closest are Dasgupta et al. (2026: windowed UNSW-NB15 evaluation under synthetic drift, no alarms, recommends balanced accuracy), Jin and Lee (2026: shift and calibrated alerting, monitoring only
recommended) and INSOMNIA (2021: windowed F1 under drift, no study of the metric's own
behaviour). Paper 1 should position itself as **an empirical study of how monitoring
metrics behave on NIDS traffic**, not as a discovery that F1 depends on prevalence.

## Consequences for Paper 1

- **Add calibrated F1 (Siblini et al.) as a comparison metric.** Reviewers will ask why
  not simply rescale F1 to a reference attack share; running it through the existing
  simulation answers that directly. *Done 2026-11-10: calibrated F1 is in the analysis
  for all runs (see `results/attack_share/README.md`, finding 3).*
- **Cite Guesné et al. for prevalence dependence and state where our results agree and
  where they qualify it** (balanced accuracy and FPR bursts).
- **Frame Strategy B's design rules** (separate recall and FPR, minimum attacks, persistence,
  pre-deployment reference) against Poenaru-Olaru et al. and Oda: alarm quality, not only
  detection, is the evaluation target.

## Limits of this search

- Database searches on 2026-11-12: IEEE Xplore (684 records), eLibrary (154) and OpenAlex as a stand-in for Scopus (1,029; Scopus access is suspended for Russian organisations). ACM DL not queried. Earlier on 2026-11-12 the IEEE and eLibrary queries were rerun as site-restricted web searches (6 studies added, none changing the novelty assessment); the database searches remain open.
- Zoghi and Serpen 2024 was read from a PDF supplied by the author of this thesis (the
  publisher page blocked automated access); the label-delay study from the author's copy.
- Russian-language literature: eLibrary searched on 2026-11-12 (Q1-Q4: 7, 16, 0 and 131
  results; one new study, pokidko2025transfer). No Russian-language study on monitoring
  deployed detectors or on metric behaviour under changing attack share was found.
