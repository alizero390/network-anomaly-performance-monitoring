# Findings: one-time test run (February test partition)

Run 2026-11-14/15 on Ali's machine (138.7 minutes) with the frozen
`configs/strategies.toml`; nothing was calibrated on test data. 10 scenarios x 200
streams x 10 label conditions; model `feb_rf`. Compare with
`results/strategies/validation/FINDINGS.md`.

## The test partition

435,843 records, attack share 0.203, recall 0.9717, FPR 0.0046, F1 0.9767. The model is
**not** weaker on test than on validation (validation: recall 0.968, FPR 0.0054), so B's
validation reference is not stale. All six scenarios and all harder variants have clean
ground truth on test (calibrated F1 change: harmless -0.004 to 0, harmful -0.108 and
-0.112).

## What held out of sample

1. **B with calibrated F1:** every harmful stream detected, no false alerts on stable or
   harmless streams, in all 9 random-label conditions. Median delays as on validation:
   6 windows (abrupt, delay 5 pooled view), 8 (attacks rare), 10-11 (gradual).
2. **B with plain F1:** false alerts on 99.6% of "fewer attacks" streams.
3. **Alert-first labels and B_ipw** (the Paper 2 result):

   | | B | B with plain F1 | B_ipw |
   |---|---|---|---|
   | False alerts, stable and harmless streams | 93.5-100% | 0% (H1: 100%) | 0-0.5% |
   | Detection, X1 hard attack mix | 60-74% | 0% (rare: 100%) | 99.5-100% |
   | Detection, X2 false-positive burst | 53-56% | 100% | 100% |

   On the real test windows under alert-first labels, B raised 3 alarms (windows 6, 46,
   58), B_ipw 1 (window 46).
4. **Strategy A as calibrated (q = 0.038)** warned on 100% of streams of every scenario,
   **before** the change: its reference sample comes from validation, and test traffic
   already differs from it. A_natural (q = 1.0) never warned. Strategy A is unusable on
   the test partition in both variants.

## What did not hold

**C-active's speed-up shrank.** On validation it was faster than B in 58% of harmful
streams (mean gain 0.77 windows); on test in 26% (mean gain 0.32 windows; never slower).
Because A already warns before the onset on test streams, its warning window often ends
before the real change, so B is not boosted when it matters. The benefit of combining
input warnings with performance confirmation depends on A's reference staying
representative, which it did not one period later.

## Real test windows in time order (no injected change)

Under random labels, B raised 1-2 alarms, at windows 45-49 and 54 (of 87). Plain F1
alarmed at 45 and 54 (once also at 6). These are real performance dips in the later part
of February 18; they have not been attributed to attack categories yet.
