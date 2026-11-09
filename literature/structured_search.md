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

**Russian-language studies** (needed for a Russian journal):

| Key | Study | What it shows | Relevance to Paper 1 |
|---|---|---|---|
| namiot2022shift | Намиот Д.Е., Ильюшин Е.А. Мониторинг сдвига данных в моделях машинного обучения // International Journal of Open Information Technologies. 2022. Т. 10, № 12. С. 84-93 ([PDF](https://injoit.ru/index.php/j1/article/download/1462/1350)) | Survey of label-free shift detection (KS, chi-square, PSI, DDM) and a monitoring architecture | Russian-language basis for Strategy A |
| kotenko2024attacks | Котенко И.В. и др. Атаки и методы защиты в системах машинного обучения // Вопросы кибербезопасности. 2024. № 1(59). С. 24-37. DOI 10.21681/2311-3456-2024-1-24-37 ([PDF](https://cyberrus.info/wp-content/uploads/2024/02/vokib-2024-1-st03-s024-037.pdf)) | Review of adversarial attacks and defences for ML | Context only; shows that journal publishes in Russian with English abstracts |
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

**Overall.** No paper found combines windowed performance monitoring of NIDS models, attack
prevalence that changes over time, alarm-level evaluation and attribution of alarms to
causes. The closest are Jin and Lee (2026: shift and calibrated alerting, monitoring only
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

- Web search only; Scopus, IEEE Xplore and ACM DL not queried.
- Zoghi and Serpen 2024 was read from a PDF supplied by the author of this thesis (the
  publisher page blocked automated access); the label-delay study from the author's copy.
- Russian-language literature: two web queries only (three studies included); a search in
  eLibrary is still needed.
