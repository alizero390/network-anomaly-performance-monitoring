# Robustness of the attack-share findings across models and capture days

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
