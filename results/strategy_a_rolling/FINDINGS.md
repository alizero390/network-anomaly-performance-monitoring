# Findings: Strategy A with a moving reference (D21)

Runs by Ali on 2026-11-23: validation (calibration, 266 min) and the one-time test run
(249 min), `scripts/run_strategy_a_rolling.py`. Settings frozen in
`configs/strategy_a_rolling.toml` before the test run (q_rolling = q_anchored = 0.038,
i.e. one changed feature out of 26; L = {0: 1, 5: 5, 10: 10}). Comparisons below are
computed from `validation/` and `test/stream_results.csv.gz`; the earlier fixed-reference
results are in `results/strategies/`.

## 1. Pre-registered success criteria (D21): both met

| Criterion (test partition) | Required | Result |
|---|---|---|
| Stable streams (S0) with an A_rolling warning | at most 10% | **0%** (fixed-reference A: 100%) |
| Harmful streams where C active is faster than B | clearly more than 26% | **54%** for C_active_rolling (never slower); fixed-reference C_active: 26% |

On validation, where the fixed reference is not stale, both variants behave alike:
C_active 58% faster than B, C_active_rolling 59%; neither is ever slower.

## 2. Resampled streams (test)

- **A_rolling**: 0% warnings on S0; warns on 100% of harmless input changes (H1-H3), as
  designed (A cannot tell harmful from harmless, D10); detects 100% of harmful changes,
  after a median of 1 window (abrupt) and 2-4 windows (gradual). The fixed-reference A
  only looked fast because it was already warning before the change (41-88% "detection",
  100% false warnings).
- Gradual changes were **not** missed, contrary to the pre-registered expectation: with a
  gap of 5 windows the reference lags far enough behind the ramp.
- **A_anchored** (B-healthy reference, d5_p100 and d5_p20): the same as A_rolling, 0%
  warnings on S0 and 100% detection. On these streams it brings nothing over A_rolling,
  and it needs labels.
- **C_active_rolling**: median delay one window shorter than B in every harmful scenario
  (e.g. X1 6 -> 5, X1 gradual 11 -> 10), no false alerts.

## 3. Real windows in time order: A stays on

On the real validation (58 windows) and test (87 windows) partitions, A_rolling flags
**every** judged window (median 92% of features changed) and so raises one warning at the
first possible window (16) that never ends. The fixed-reference A did the same on test.

The rolling reference therefore removes the *staleness* problem of the resampled streams,
but not the problem of real traffic: consecutive real windows differ in almost every
feature by a statistically significant amount. With 5,000 records per window and a
20,000-record reference, the Kolmogorov-Smirnov and chi-square tests detect differences
far too small to matter. This is the statistical-versus-practical significance problem
already listed for D10 ("practical-significance floor"); it is now the main open
weakness of Strategy A.

Consequence for C on real windows: C_active_rolling raises exactly B's alarms (A's
permanent warning adds no timing information), so C does no harm but no good there.

## 4. B differs slightly from the earlier runs

The script checks B against the earlier strategy runs and reports "DIFFERENT" on both
partitions. Row by row (20,000 B rows each), 17% (validation) and 21% (test) of rows
differ, almost all in the alert-first condition (number of false alerts, e.g. 2 vs 1) and
in the gradual and rare scenarios (detection delay +-1 window); abrupt scenarios and S0
under random labels match. Detection and false-alert rates are unchanged. Part of the
cause on validation is that the frozen config stores reference values rounded to 6
decimals while the earlier validation run used unrounded values; the cause on test is
not yet identified. The D21 comparisons are unaffected: B, A_rolling and
C_active_rolling come from the same run and share every label draw.

## 5. Next

- D22 (proposal): a practical-significance floor for Strategy A (a minimum effect size
  per feature, e.g. Kolmogorov-Smirnov statistic or Cramer's V, besides the p-value),
  calibrated on real validation windows; it decides whether A can be used on real traffic.
- Find the cause of the remaining B differences (section 4).
