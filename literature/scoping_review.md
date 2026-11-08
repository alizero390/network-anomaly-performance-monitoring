# Scoping review: positioning the attack-share findings

First pass, 2026-11-08. Purpose: decide what is already known and what the
`results/attack_share` findings can claim as new. This is a scoping search with a web
search engine, not a systematic review: before submission, repeat the searches in
Scopus, IEEE Xplore, ACM DL and Google Scholar and log them in `search_log.md`.

## 1. What is already known

### UNSW-NB15 composition and hard categories

- **Generic dominates the attacks.** About 65% of all UNSW-NB15 attack records are
  Generic [zoghi2024unswviz]. (Our validation partition: 69%.)
- **Generic's ground truth is unclear.** Its definition "involves block cipher
  vulnerabilities" and it scores high on the "unclear ground truth" smell
  [flood2024badsmells].
- **Fuzzers and Exploits overlap with normal traffic.** Fuzzers and Normal records
  cluster together in t-SNE/PCA projections, and Exploits overlap Normal
  [zoghi2024unswviz]. Fuzzers contain "dubious routing attacks" with no CVE that only
  alter minor protocol aspects, producing benign-looking flows [flood2024badsmells].
- **Simple features separate classes.** Protocol and TTL alone separate benign from
  attack traffic with 98% accuracy; TTL fingerprints operating systems
  [flood2024badsmells].
- **Attacks run concurrently.** In UNSW-NB15 all attack classes were injected at the
  same time on the attack days; the authors recommend analysing classes individually
  [luay2025temporal] (NetFlow version of the dataset).

**Consequence for us:** Generic dominance and Fuzzers' difficulty are *known at the
dataset level*. We must cite them and must not present them as discoveries.

### Evaluation pitfalls

- Base rate fallacy, inappropriate performance measures, and temporal snooping are
  named pitfalls in security ML [arp2022dos].
- Time-aware evaluation (train on the past, test on the future) and its metric AUT
  [pendlebury2019tesseract].
- "High F1 scores are not enough to validate a NIDS model's performance"
  [flood2024badsmells].

### Drift and monitoring in NIDS

- INSOMNIA handles concept drift with scarce labels (active learning plus pseudo-labels)
  on corrected CICIDS2017, evaluated over count-based windows with windowed F1 and
  AUT(F1). It notes that low-prevalence attacks are hard to detect
  [andresini2021insomnia]. This confirms windowed F1 is standard practice in NIDS drift
  work.
- Recent work separates "drift was detected" from "a retrained model should replace the
  deployed one", with class-balanced windows, label latency models and UNSW-NB15
  scenarios. It explicitly does not model prevalence and does not analyse category
  composition [fernandezbarrios2026promotion].
- Label scarcity in cyberthreat detection is surveyed in [apruzzese2022sokunlabelled].

### Monitoring with delayed or missing labels (general ML)

- Whether a change is detectable at all depends on label delay [zliobaite2010delayed].
- Input-shift detection methods, compared empirically [rabanser2019failing]: the
  ancestor of Strategy A.
- Label-free performance estimation from model confidence: ATC [garg2022atc] and PAPE /
  CBPE-style estimators under covariate shift [bialek2024pape].
- Label (prior) shift estimation with a black-box predictor [lipton2018bbse].
- Proxy monitoring under delayed ground truth in fraud detection; concept drift with
  constant P(X) was not detected by any proxy [solozobov2026evidence].

## 2. What we did not find

No paper found in this pass:

1. Measures, over time, how the **attack-category mix** of a NIDS stream drives
   **window-level** performance metrics, and separates that from attack-share
   arithmetic and from within-category change.
2. Shows that, on an unchanged UNSW-NB15 stream, degradation alarms from a windowed
   metric rule depend on the **choice of reference period**, because that period is
   itself a different traffic regime.
3. Quantifies how often an F1/MCC-drop rule raises **false degradation alarms** when only
   the attack share falls into realistic ranges (≤2%), compared with recall or balanced
   accuracy, for a NIDS model.

"Not found in a scoping search" is not "does not exist". Items 1-3 are the candidate
contribution; the systematic search must try hard to falsify them.

## 3. Proposed framing for paper 1

> Known dataset-level properties of UNSW-NB15 (Generic dominance, Fuzzers overlapping
> normal traffic) have a temporal consequence that matters for monitoring deployed
> detectors: because the category mix moves over time, window-level metrics move with
> it, and degradation alarms depend on the reference period and the metric rather than on
> any change to the model.

Evidence needed beyond the current baseline (in progress):

- A second model (gradient boosting) on the same split: `results/runs/feb_hgb`.
- An independent capture day (January 22-23): `results/runs/jan_rf`, `jan_hgb`.
- Optionally a second dataset: corrected CICIDS2017 [engelen2021cicids2017], which
  INSOMNIA also uses, so results would be directly comparable.

## 4. Suggested target venues (check scope and deadlines)

- Workshop or short paper: ACM AISec (co-located with CCS), where INSOMNIA appeared.
- Dataset and evaluation critiques: venues that published [flood2024badsmells] and
  [engelen2021cicids2017] (IEEE EuroS&P, IEEE S&P Workshops).

## 5. Next searches

| Query idea | Why |
|---|---|
| "UNSW-NB15" AND (temporal OR chronological) AND (drift OR window) | Check novelty of item 1 |
| intrusion detection AND "reference window" AND degradation | Check item 2 |
| (prevalence OR "class imbalance" OR "base rate") AND monitoring AND F1 AND alarm | Check item 3 |
| per-class OR per-category evaluation intrusion detection "Generic" | Prior reporting of category-stratified results |
| performance estimation without labels AND intrusion detection | Strategy C competitors in NIDS |
