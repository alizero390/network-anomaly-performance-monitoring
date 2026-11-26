# Findings: Strategy A with a minimum effect size (D22)

Runs by Ali on 2026-11-26: validation (calibration, 79 min) and the one-time test run
(77 min), `scripts/run_strategy_a_floor.py`. Frozen settings
(`configs/strategy_a_floor.toml`, committed before the test run): epsilon = 0.3, q = any
changed feature (1e-9), rolling reference and L from D21. D21's A_rolling and
C_active_rolling rows on the same streams are included in `stream_results.csv.gz`.

## 1. Calibration: no epsilon separates normal variation from change

Share of judged real validation windows (time order, rolling reference) with at least
one changed feature, by epsilon:

| epsilon | 0.02 | 0.03 | 0.05 | 0.075 | 0.10 | 0.15 | 0.20 | 0.30 |
|---|---|---|---|---|---|---|---|---|
| windows flagged | 100% | 100% | 98% | 98% | 93% | 73% | 55% | 27% |

No grid value met the 5% target, so the pre-registered fallback (largest value, 0.3)
was used. Consecutive real windows differ by Kolmogorov-Smirnov statistics or category
shifts above 0.3 in a quarter of all windows: normal UNSW-NB15 traffic is far from
stationary at a 5,000-record window.

## 2. Pre-registered criteria on test

| Criterion | Target | Result | |
|---|---|---|---|
| Stable streams (S0) with a warning | at most 10% | 0% | met |
| Judged real test windows flagged | at most 10% | 21% (15 of 73) | not met |
| Harmful streams detected by A_floor | at least 80% | 0% (every harmful scenario) | not met |
| C_active_floor never slower than B | always | never slower (and never faster) | met |

Validation gave the same picture (27% of real windows flagged, 0% detection). At the
floor needed to quiet real traffic, the controlled harmful changes (attack-mix and
false-positive shifts) move no feature by 0.3, so A_floor never warns on them; on
harmless input changes it warned in 28% of H2 streams on test. D22 therefore fails.

## 3. Real test windows: one coherent input change before B's alarms

Flagged real test windows (features: UNSW-NB15 column names):

- windows 43-49: dur, Sload and, from window 44, dbytes, dttl, Dload, Dpkts, Dintpkt and
  state change together; A_floor warns at window 44;
- windows 59-62: 88-92% of all features change (a large traffic shift); A_floor warns at
  window 60.

B's alarms on the same windows fall at 45-54 (depending on label delay and availability),
and with A_floor's warning C_active_floor raises them about 5 windows earlier in every
random-label condition (e.g. 44 instead of 49, 49 instead of 54, 54 instead of 59). This
is one real event: suggestive that large input shifts can precede measured degradation,
not evidence. The shift at windows 59-62 has no B alarm.

## 4. Conclusion for RQ1 and RQ3 (D10, D21, D22 together)

1. **Fixed reference (D10):** stale one period later: 100% false warnings on test.
2. **Rolling reference (D21):** removes staleness on controlled streams (0% false
   warnings, 100% detection, C faster than B in 54% of harmful streams), but flags every
   real window: statistical significance is reached by trivially small differences.
3. **Minimum effect size (D22):** no floor quiets real traffic and keeps detection; at
   the floor that comes closest, controlled harmful changes are no longer seen.

Label-free input monitoring cannot replace label-based monitoring on this traffic: the
natural variation of real network traffic is as large as the input effect of the
changes that harm the detector. Its value is as an early hint inside Strategy C, where
it never delays B's alarms and, for large shifts, can bring them forward.
