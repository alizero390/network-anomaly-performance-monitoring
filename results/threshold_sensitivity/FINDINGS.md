# Findings: sensitivity of Strategy B to the alarm drop (D23, part 2)

Runs 2026-11-26 on Ali's machine (validation 13.8 min, test 15.0 min;
`scripts/run_threshold_sensitivity.py`). Drops 0.03, 0.05 (the thesis value, D9) and
0.10; everything else frozen in `configs/strategies.toml`; 10 scenarios x 200 streams x
10 label conditions. All three drops of one partition share the same streams and label
draws, so they are paired.

## 1. Random labels: 0.05 sits in a flat region

| B, random labels pooled | 0.03 | 0.05 | 0.10 |
|---|---:|---:|---:|
| False alerts, stable and harmless (validation / test) | 0% / 0% | 0% / 0% | 0% / 0% |
| Detection, harmful (min over scenarios, validation / test) | 100% / 100% | 100% / 99.8% | 94.3% / 85.3% |
| Median delay, X1 gradual (validation / test) | 8 / 9 | 10 / 11 | 15 / 16 |
| Median delay, X1 rare (validation / test) | 8 / 8 | 8 / 8 | 11 / 12 |
| Harmful, 20% labels: detection / mean median delay (test) | 100% / 8.9 | 99.9% / 9.5 | 91.6% / 11.8 |

- **Lowering the drop to 0.03 costs nothing under random labels**, against the D23
  expectation: no false alerts in any condition, including 20% labels, and gradual
  changes are caught 1-2 windows earlier. The eligibility rule (n_min attacks, m_min
  normals, pooling) already keeps cohort noise below 0.03.
- **0.10 is too high.** It equals the harm boundary of D4, so changes just above it are
  missed: detection falls to 85% (X1 rare) and 97-98% (gradual), delays grow by 3-5
  windows.

## 2. Alert-first labels: 0.05 is the only usable value for B_ipw

| False alerts on H1 (fewer attacks), alert-first | 0.03 | 0.05 | 0.10 |
|---|---:|---:|---:|
| B (unweighted), validation / test | 100% / 100% | 100% / 96.5% | 0.5% / 0% |
| B_ipw, validation / test | 39.5% / 27.0% | 0.5% / 2.0% | 0% / 0% |
| B_ipw detection, X1 gradual (test) | 100% | 100% | 77.0% |

- Unweighted B under alert-first labels cannot be fixed by the threshold: at 0.03 and
  0.05 it alarms on almost every stream; at 0.10 the false alerts vanish but so does
  detection of the hard attack mix (0% on test). The bias, not the threshold, is the
  problem (Chapter 8).
- With weighting, 0.03 gives 27-40% false alerts when attacks become rare (the weighted
  estimate is noisier), and 0.10 loses detection (77-94% on X1). 0.05 is the only value
  that is clean in both directions.

## 3. Plain F1 is not saved by a larger threshold

B_F1 false alerts on H1 (random labels): 100% at 0.03 and 0.05; 89.5% (validation) and
54.5% (test) at 0.10. The attack-share problem of plain F1 (Chapter 4) is larger than any
sensible threshold.

## 4. Real windows in time order

| B, test, d0_p100 | 0.03 | 0.05 | 0.10 |
|---|---|---|---|
| Alarm windows | 45, 54 | 49, 54 | none |

All of B's alarms fall inside the degraded period 44-56 (`results/test_alarm_attribution/`); window 45 has a full-label drop of 0.041, so it counts as degraded at the 0.03 threshold.
At 0.03, B confirms the hard-mix period 4 windows earlier; at 0.10 it misses it entirely
under full labels, although calibrated F1 fell by up to 0.20. B_F1 at 0.03 adds alarms
at windows 6 and 34, which are not degraded windows.

## 5. Conclusion for the thesis

The threshold of 0.05 stays (D9, D23: no recalibration). It is not on a knife edge:
results under random labels are the same at 0.03, and 0.05 is the only value that also
works with weighted alert-first labels. 0.10 is too coarse for changes near the harm
boundary. An operator with random audit labels could use 0.03 for earlier detection.

## 6. Reproduction check and a fixed bug

The check against the D14 runs reported "DIFFERENT" (15% of rows on validation, 17% on
test), concentrated in the gradual (51-58%) and rare (15-25%) scenarios. The real-window
results matched exactly (30 of 30 rows on both partitions). Cause, found 2026-11-26:
`scenarios._blend` and `shift_mix` built the stratum mixes from Python sets, whose order
depends on the string-hash seed that changes with every Python process. The order
decides which stratum receives which multinomial draw in `build_stream`, so the same
seed gave a different (equally valid) set of resampled streams in every run. Fixed by
sorting the keys; `tests/test_scenarios.py` now checks that streams are identical under
three hash seeds. Consequences:

- Every earlier run is a valid random sample of streams, and every comparison in the
  thesis and papers is between strategies of the same run, which share the same streams
  and label draws. No conclusion changes.
- Results of the resampled scenarios were not reproducible bit for bit before the fix;
  they are from now on. This also explains the unexplained B differences of the D21 and
  D22 runs (`results/strategy_a_rolling/FINDINGS.md`, section 4).
- The real-window (time-ordered) runs never used the affected code.
