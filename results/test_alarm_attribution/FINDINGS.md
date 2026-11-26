# Findings: attribution of the real test-window alarms (D23, part 1)

Run 2026-11-26 on Ali's machine (`scripts/attribute_test_alarms.py`), February test
partition, 87 windows of 5,000 records in time order, all labels (the truth). Descriptive
only: nothing was tuned. Details in `summary.md`, `windows.csv`, `categories.csv`.

## 1. Every flagged window is a real loss of recall on Fuzzers

11 of 87 windows have calibrated F1 at least 0.05 below the reference (0.9728): windows 2,
5, 44, 46, 48, 49, 50, 53, 54, 56 and 66. All 11 have the cause **missed attacks**
(recall 0.67-0.89 against 0.968 on validation), and in every one Fuzzers account for
88-100% of the missed attacks. None is an attack-share effect, a false-positive burst
alone or a window with too few attacks. Every alarm that B, B_ipw and C_active_natural
raised on the real test windows under random labels falls inside the degraded period
44-56: at windows 48, 49 or 54 (flagged windows) in 13 of its 14 alarms over the nine conditions (B_ipw and C_active_natural identical), and once
at window 45 (50% labels), which confirms windows 44-45; window 44 is flagged and window
45 misses the 0.05 mark with full labels by a little (drop 0.041). **None of B's
real-traffic alarms is a false alarm.**

## 2. The dip of windows 43-57 is mostly a change of attack mix

In windows 43-57 (later part of 18 February):

| | Windows 1-42 | Windows 43-57 | Windows 58-87 |
|---|---:|---:|---:|
| Attack share (median) | 22.5% | 6.5% | 24.0% |
| Generic, share of attacks | 73.7% | 7.8% | 73.4% |
| Exploits | 11.9% | 39.2% | 10.3% |
| Fuzzers | 4.2% | 27.7% | 5.3% |
| Reconnaissance | 3.4% | 14.9% | 3.1% |
| Fuzzers recall | 0.65 | 0.53 | 0.57 |

Generic attacks, which the model detects almost perfectly, nearly disappear; Fuzzers,
which it detects about 60% of the time, grow six-fold. Recall over the period falls
from 0.978 (all other windows) to 0.865. With the other windows' per-category recall,
the period's mix alone gives 0.885: **about 80% of the drop is the change of mix and
about 20% lower recall within Fuzzers.** The median FPR also rises (0.37% to 0.56%, with
windows 45-50 and 56 at 1.1-1.8%). This is the controlled scenario X1 (hard attack mix)
occurring naturally, and a calibrated-F1 drop of 0.10-0.20 in windows 44, 48, 50 and 53
is harmful by the D4 definition.

## 3. Plain F1 alarms earlier for a partly wrong reason

B_F1 confirmed at window 45, where calibrated F1 (0.932) is not flagged but plain F1
(0.904) is: with only 9% attacks, the window's false positives weigh more in precision.
B (calibrated F1) confirmed at window 49 (two consecutive flagged windows, 48-49). Both
see the same event; plain F1's earlier alarm comes partly from the low attack share.

## 4. Other alarms

- Window 2 (A's warning and C_active's alarm under the stale fixed reference): window 2
  is flagged too (recall 0.76, 68 Fuzzers missed of 282 attacks), but A warned on
  every window there (`results/strategies/test/FINDINGS.md`), so this is a coincidence,
  not evidence for A.
- Alert-first alarms at windows 6 and 58 (B) are not flagged windows: they are
  false alarms caused by the biased labels (Chapter 8); B_ipw raised only the alarm at 46,
  which is flagged.
- D22's A_floor warned at window 44, the first window of the mix change: the input
  shift is real and coincides with the dip.

## 5. For the thesis

Chapter 6, real traffic: the only performance problem in the test period is a
period of hard attack mix; B detects it under every random-label condition and raises no
false alarm on real traffic. Chapter 7: A_floor's warning at 44 is the one case where an
input warning came before a confirmed degradation.
