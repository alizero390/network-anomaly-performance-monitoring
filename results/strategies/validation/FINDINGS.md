# Findings: strategy comparison on February validation

Full run, 2026-11-12 (Ali's machine, 127 minutes): 10 scenarios x 200 streams x 10 label
conditions, Random Forest `feb_rf`. Numbers below from `summary.csv`,
`paired_*.csv` and `natural_validation.csv` in this folder. Calibrated values in
`configs/strategies.toml`: Strategy A q = 0.038 (one feature of 26), association period
L = 1 / 5 / 10 windows for label delay 0 / 5 / 10, n_min = 68.

## 1. With random label availability, B (calibrated F1) is reliable

- Every harmful stream was detected (event recall 100% in all 9 random conditions and
  all 6 harmful scenarios).
- No false alerts on stable or harmless streams (0% in every random condition).
- B with plain F1 false-alarmed on **every** "fewer attacks" (H1) stream in every
  condition (McNemar p < 1e-59 against calibrated F1): the Paper 1 effect inside the
  strategy comparison.

## 2. Label delay sets the detection delay; scarce labels add to it

Median detection delay of B, in windows after the onset:

| Scenario | delay 0 (100% / 50% / 20% labels) | delay 5 | delay 10 |
|---|---|---|---|
| X1 or X2, abrupt | 1 / 1 / 1 | 6 / 6 / 6 | 11 / 11 / 11 |
| X1 or X2, attacks rare (2%) | 1 / 3 / 7 | 6 / 8 / 12 | 11 / 13 / 17 |
| X1 gradual (10 windows) | 5 / 5 / 5 | 10 / 10 / 10 | 15 / 15 / 15 |
| X2 gradual | 4 / 4 / 4 | 9 / 9 / 9 | 14 / 14 / 14 |

- Abrupt change: delay = label delay + 1 window (two cohorts are needed).
- When attacks are rare, labelled attacks per window fall below n_min = 68, cohorts are
  pooled, and 20% labelling adds 6 windows on top of the label delay.

## 3. Strategy A is fastest on streams but warns on everything

- A detected every harmful stream 1-3 windows after the onset, earlier than any B.
- A warned on 100% of harmless streams (H1-H3): it cannot tell harmful from harmless.
- On the **real validation windows in time order**, A flagged 100% of windows (median
  96% of features changed). Its threshold came from resampled stable streams, which have
  no real day-to-day variation. As calibrated, A carries no information on real traffic.

## 4. Active C is one window faster than B, at no false-alert cost

- C-active cut the median delay by 1 window in most harmful scenarios and conditions
  (Wilcoxon p between 1e-45 and 1e-4), with no change in false alerts under random
  labels.
- No gain where cohorts are pooled (attacks rare, 20% labels), because a pooled cohort is
  one evaluation anyway.
- C-passive raises exactly B's alarms; its value is labelling A's warnings.

## 5. Alert-first labelling breaks performance monitoring

When analysts label predicted attacks first (90%) and normal records rarely (10%):

- B (calibrated F1) false-alarmed on 100% of stable and harmless streams: labelled normal
  records are mostly false positives, so the estimated FPR is far too high.
- Its detection of harmful changes fell to 4-11%, because the false alarm before the onset
  leaves the monitor in the alarm state, so the real change is never raised separately.
- B with plain F1 did not false-alarm, but missed X1 entirely (0%): with biased labels
  missed attacks are rarely labelled, so recall is overestimated.
- This is the strongest result for research question 4 so far: *which* labels arrive
  matters more than how many or how late.

## 6. Real validation windows in time order

B (calibrated F1) raised 2 alarms in every random condition: at the start (window 2) and
near the end (windows 54-56), the low-Fuzzers-recall periods found in Paper 1. Plain F1
raised one more in the middle (window 7, 10 or 52-53 depending on the condition).

## Open decisions before the test run

1. A correction for biased labels (inverse-probability weighting with the known labelling
   probabilities) as an extra variant of B.
2. Calibrating Strategy A's threshold on the real time-ordered validation windows instead
   of resampled stable streams, as an extra variant of A.
Both change `configs/strategies.toml`, so they must be settled before the test partition
is used (design spec D1).
