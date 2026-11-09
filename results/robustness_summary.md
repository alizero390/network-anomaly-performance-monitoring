# Robustness of the findings across models, capture days and datasets

Four runs: two models (Random Forest `rf`, histogram gradient boosting `hgb`) on two
UNSW-NB15 capture days (February 18: frozen 50/20/30 split; January 22: attack period
split 50/50, see RESEARCH_DECISIONS.md section 13). Full numbers: `comparison.md`.
Per-run details: `attack_share/` (baseline) and `runs/<run>/attack_share/`.

January's validation is short (18 windows, 93,356 records), so January is a supporting
replication, not a second primary experiment.

## Replicates in all four runs

**1. Fuzzers cause almost all missed attacks.**

| | feb_rf | feb_hgb | jan_rf | jan_hgb |
|---|---:|---:|---:|---:|
| Fuzzers recall | 0.581 | 0.886 | 0.780 | 0.940 |
| Fuzzers share of all missed attacks | 89% | 90% | 94% | 98% |

The level of Fuzzers recall depends on the model, but in every run Fuzzers are the
dominant source of misses. This agrees with the dataset-level overlap of Fuzzers and
normal traffic reported by Zoghi and Serpen and by Flood et al.

**2. Under pure attack-share change, F1 and MCC raise false degradation alarms;
recall and balanced accuracy do not.** Share of simulated 20-window streams that
alarm when only the attack share changes (model behaviour held fixed):

| Attack share | F1 (all runs) | MCC (all runs) | Balanced accuracy (all runs) | Recall (all runs) |
|---:|---:|---:|---:|---:|
| 1% | 100% | 100% | 0% | 0-3% |
| 5% | 25-100% | 11-100% | 0% | 0% |
| ≥10% | ≤6% | ≤3% | 0% | 0% |

At 5%, the rate depends on the model's false positive rate: feb_rf, the run with the
lowest FPR (0.5%), alarms in 25% (F1) and 11% (MCC) of streams; the other three runs
(FPR 1.6-2.4%) alarm in 100%.

## Holds, with model- and day-dependent size

**3. Window F1 varies mostly because detection changes.** Each window's own recall
and FPR explain R² = 0.88-0.92 of window F1 in three runs; attack share alone explains
0.11-0.17. The exception is feb_hgb (0.50 vs 0.42): its higher FPR makes precision,
and so F1, more sensitive to the attack share.

**4. The attack-category mix explains part of window recall.** R² = 0.67 (feb_rf),
0.48 (feb_hgb), 0.31 (jan_rf), 0.50 (jan_hgb). The effect is largest where Fuzzers
recall is lowest and where the attack share varies most (February).

## Does not replicate

**5. Reference-period sensitivity.** In February, the first-10-window reference and
the all-window reference disagree sharply (first F1 alarm at window 57 vs window 2),
because February's first 10 windows are a low-attack, low-performance period. In
January both references give the same alarms. This finding is specific to February's
traffic and should be presented as such.

## New nuance from January: false positive bursts

In January, F1 and MCC confirm alarms at windows 12-14 in both runs while balanced
accuracy and recall do not. Those windows have **no recall problem** (jan_hgb recall
0.98-1.00) but a **false positive burst**: FPR rises from under 1% to 4-5% (jan_rf) and
5-9% (jan_hgb), and precision falls to 0.50-0.75.

This is a real operational degradation (many more false alerts), and F1 detects it.
Balanced accuracy barely moves, because it averages recall with 1 − FPR, so an FPR rise
from 0.5% to 5% lowers it by only about 0.02. So balanced accuracy is not a safe
replacement for F1 either: it is robust to attack-share change but blind to FPR
increases that matter in practice.

**Implication for Strategy B:** monitor recall and FPR (or the number of false alerts
per window) as separate signals instead of any single combined metric. F1 conflates a
fall in attack share with an FPR rise; balanced accuracy hides the FPR rise.

## Summary for the paper

| Finding | Status |
|---|---|
| Fuzzers dominate misses | Replicates in 4/4 runs |
| F1/MCC false alarms under attack-share change; recall and balanced accuracy unaffected | Replicates in 4/4 runs |
| Window F1 driven mostly by real recall/FPR change | 3/4 runs; weaker for high-FPR model |
| Category mix explains window recall | 4/4 runs, R² 0.31-0.67 |
| Reference period decides alarms | February only |
| Balanced accuracy misses FPR bursts | Observed in January (2/2 runs) |

## Second dataset: improved CIC-IDS-2017 (added 2026-11-09)

Train Monday-Thursday, monitor Friday (109 windows; RESEARCH_DECISIONS.md, section 14).
Each attack type runs in its own 1-2 hour block, so Friday mixes attack-free hours with
Botnet (unseen), Portscan and DDoS (related to, but not the same labels as, training
attacks). Numbers: `runs/cic_rf/`, `runs/cic_hgb/`, `comparison.md`,
`cicids2017_findings.xlsx`.

| | cic_rf | cic_hgb |
|---|---:|---:|
| Friday recall: Botnet / DDoS / Portscan | 0.000 / 0.448 / 0.902 | 0.000 / 0.998 / 0.990 |
| Pooled FPR | 0.000 | 0.0004 |
| Simulated F1 false-alarm rate at 1% attacks | 16% | 5% |
| Simulated recall false-alarm rate at 1% attacks | 65.5% | 0% |
| R² of window recall: category mix | 0.73 | 0.76 |

- **Unseen attacks are missed entirely** (Botnet recall 0 for both models).
- **The reference-period effect replicates in its most extreme form.** Friday's first 10
  windows contain almost no attacks: the reference F1 is 0 and recall and MCC are
  undefined, so no metric can alarm, including during the Botnet hour.
- **Attack-share false alarms follow FPR across all six runs:** near-zero-FPR models
  (CIC) have F1 false-alarm rates of 5-16% at 1% attacks; every UNSW-NB15 run (FPR
  0.5-2.4%) has 100%.
- **Recall becomes noisy when attacks are rare:** with about 50 attacks per window and
  recall 0.73, chance alone moves window recall by about 0.063, more than the 0.05
  threshold.

## Alarm attribution (all six runs)

`alarm_attribution/summary.md` labels every confirmed alarm window by cause (missed
attacks, false-positive burst, too few attacks to judge, attack-share effect).

- With the all-window reference, **almost every CIC-IDS-2017 recall alarm is real**:
  missed Botnet, DDoS or Portscan attacks.
- **January alarms are all false-positive bursts**; February alarms are mostly missed
  Fuzzers, plus (feb_hgb) false-positive bursts and attack-share effects.
- **F1 and MCC add harmless alarms** that recall does not raise: windows without attacks
  but with a few false positives (F1 = 0; cic_hgb: 21 of 34 F1 alarms) and pure
  attack-share effects (MCC; cic_hgb: 11 of 13).
- **Trade-off of a minimum-attack eligibility rule.** cic_rf misses every Botnet flow in
  11 consecutive windows, but 8 of them contain fewer attacks (13-85) than the
  noise-based minimum (79), so such a rule would suppress most of that real alarm. A
  persistence rule (same failure over many consecutive small windows) is a candidate
  complement.

**Implication for Strategy B:** monitor recall and FPR as separate signals, require a
minimum number of labelled attacks per window, add a persistence rule for consistently
zero recall, and take the reference from labelled data before deployment rather than
from the first monitored windows.

Window times run 11:59-19:57 on 2017-07-07 (corrected 2026-11-10 after a unit bug that
showed 1970 dates; all metrics were unaffected). The first confirmed alarms fall at
13:02, in the Botnet hour.
