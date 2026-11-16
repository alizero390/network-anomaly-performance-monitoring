# Findings: label-bias study (Paper 2), validation and test

Fixed grid (RESEARCH_DECISIONS.md D17, D18): 32 label conditions x 6 scenarios x 200
streams, label delay 5 windows, frozen `configs/strategies.toml`, model `feb_rf`.
Validation run 2026-11-15 (11.0 min, after the D18 addition and pooling fix); test run the
same day (13.5 min) as confirmation. `p_alert` = share of alerts labelled, `p_normal` =
share of records predicted normal that are labelled. Tables: `*/policy_table.csv`.
Validation (V) and test (T) agree on every message below.

## 1. Uncorrected monitoring breaks once normal traffic is labelled at 10% or less

B (calibrated F1), p_alert 0.9:

| p_normal | False alarms, stable/harmless (V / T) | Harmful changes caught (V / T) |
|---|---|---|
| 0.50 | 0% / 0% | 100% / 100% |
| 0.20 | 0.5% / 0% | 99% / 85% |
| 0.10 | 100% / 99% | 9% / 59% |
| 0.05 | 100% / 100% | 0% / 0% |
| 0.02 | 97% / 72% | 40% / 71% |

Plain F1 (B_F1) instead misses the Fuzzers change under every biased policy (75% = only X2
found) while never false-alarming on stable streams.

## 2. Weighting repairs it down to 5% labelling of normal traffic

B_ipw (approved eligibility rule): false alarms 0-1.8% (V) and 0-1% (T) under every
policy; harmful changes caught 99-100% for p_normal >= 0.05 on both partitions.

## 3. Below 5%, the eligibility rule decides, and only the effective-sample-size rule is honest

| p_alert 0.9 | B_ipw | B_ipw_eff | B_ipw_ess |
|---|---|---|---|
| p_normal 0.05: false alarms | 1% / 0.8% | 17% / 12% | 0.5% / 0% |
| p_normal 0.05: caught | 99.9% / 99% | 100% / 100% | 99% / 99% |
| p_normal 0.02: false alarms | 0% / 0.2% | 5% / 3% | 0% / 0% |
| p_normal 0.02: caught | 85% / 71% | 97% / 97% | 25% / 25% |
| p_normal 0.01: false alarms | 0% / 0% | 6% / 4% | 0% / 0% |
| p_normal 0.01: caught | 50% / 50% (artefact) | 86% / 87% | 0% / 0% |

(V / T in each cell.)

- B_ipw at 1%: only false-positive bursts are "caught", because the burst itself creates
  enough labelled normals to pass the rule. Eligibility, not the metric, raises the alarm.
- B_ipw_eff catches most changes at 1-2% but pays with false alarms (up to 17% at 5%).
- **B_ipw_ess** never false-alarms (at most 1% anywhere) and simply stays silent when the
  labels cannot support a judgement: at 1% nothing, at 2% only the rare-attack false-positive
  burst (X2_rare, where windows hold more normal records).
- This matches a simple bound: the effective number of labelled normal records per cohort is
  about p_normal x (normal records per window) x (windows pooled). To reach m_min = 500 with
  ~4,000 normal records per window and at most 5 windows, p_normal must be at least about
  500 / (4,000 x 5) = 2.5%. Below that, monitoring is not possible at this precision.

## 4. Wrong labelling rates: the effective-sample-size rule also removes the dangerous case

True (0.9, 0.1), assumed p_normal halved: false alarms B_ipw 24% / 20%, B_ipw_eff 35% / 31%,
**B_ipw_ess 1% / 1%** (caught 94% / 93%). Doubling the assumed rate or assuming
p_alert 0.7 is nearly harmless for all three. At the 2% audit rate, every wrong assumption
leaves B_ipw_ess largely silent rather than wrong.

## Messages for Paper 2

1. Alert-first labelling breaks performance monitoring of intrusion detectors once normal
   traffic is labelled at about 10% or less: calibrated F1 floods with false alarms, plain
   F1 silently misses attacks.
2. Inverse-probability weighting with known labelling rates repairs it down to 5%, with no
   tuning, confirmed on held-out test data.
3. Use the effective sample size of the weighted labels to decide when a window can be
   judged: it removes false alarms (also under wrongly assumed rates) and makes the
   monitor stay silent, not wrong, when labels are too few.
4. Practical requirement: audit at least ~2.5-5% of unflagged traffic (bound above), and
   when the audit rate is uncertain, assume it higher rather than lower.

## 5. Second detector: feb_hgb (D19, run 2026-11-16)

Same grid, rule and settings; feb_hgb's own reference values (recall 0.9913, n_min 19,
calibrated F1 0.9614; `configs/reference_feb_hgb.toml`). Outputs in
`results/label_bias/feb_hgb/`.

**Which scenarios exist.** The same construction rule gives fewer harmful scenarios for
the stronger detector:

| | S0, H1 | X1 (Fuzzers) | X2 (false-positive burst) |
|---|---|---|---|
| Validation | usable | not harmful at any alpha | harmful at alpha 0.3 (FPR 1.8% -> 7.8%) |
| Test | usable | not harmful | not harmful at any alpha |

So on test, feb_hgb confirms only the false-alarm side; detection evidence for feb_hgb
comes from validation X2 and X2_rare. The rule was not changed after the test run.

**Results (p_alert 0.9; V = validation, T = test):**

| p_normal | B false alarms (V / T) | B_ipw false alarms | B_ipw caught (V) | B_ipw_ess false alarms | B_ipw_ess caught (V) |
|---|---|---|---|---|---|
| 0.20 | 100% / 100% | 0% / 0% | 100% | 0% / 0% | 100% (delay 6) |
| 0.10 | 100% / 100% | 0% / 0% | 100% | 0% / 0% | 100% (delay 8) |
| 0.05 | 100% / 100% | 0% / 0% | 100% | 0% / 0% | 100% (delay 10) |
| 0.02 | 100% / 100% | 0.2% / 0% | 100% | 0% / 0% | 50% (X2_rare only, delay 14) |
| 0.01 | 100% / 60% | 0.2% / 0.2% | 100% (burst artefact) | 0% / 0% | 0% |

Unweighted B catches none of the bursts under biased labels (0-6% at p_alert 0.9).
Wrong rates: halving the assumed p_normal at (0.9, 0.1) gives false alarms of 4.5% / 3.5%
for B_ipw and 1% / 0.2% for B_ipw_ess, and lowers detection (B_ipw 46%, B_ipw_ess 33%);
doubling it or assuming p_alert 0.7 changes almost nothing.

**Conclusion.** Every message above holds for a second, stronger detector: alert-first
labels break unweighted monitoring at 20% or less normal labelling (feb_hgb is more
sensitive than feb_rf, which still worked at 20%); weighting repairs it; the
effective-sample-size rule gives 0% false alarms and goes silent below about 2%. New
message: a stronger detector has fewer harmful changes to find (X1 does not exist for
feb_hgb; on test, neither does X2), so the size of a harmful change must be reported per
detector.

## 6. Second dataset: CIC-IDS-2017 Friday in time order (D20, run 2026-11-16)

Detectors cic2_rf and cic2_hgb (split D2), reference from the validation half of Thursday,
Friday monitored in time order, 32 label conditions x 200 label draws. Outputs in
`results/label_bias/cic2_<model>/` (`windows.csv` has the ground truth per window).

**Ground truth.** Neither detector raises false positives (0-2 on Friday), so every
change is a change of recall.

| Detector | Reference recall / calibrated F1 | Harmful events on Friday |
|---|---|---|
| cic2_rf | 0.195 / 0.327 | 2: a Portscan variant missed completely (17:54-17:56, windows 55-70, recall 0) and DDoS (18:54-19:16, windows 83-105, recall 0.01-0.05) |
| cic2_hgb | 0.516 / 0.681 | none: Friday recall (0.81-0.99 Portscan, 0.59-0.68 DDoS) is above the reference |

Botnet (13:02-13:55, recall 0 for both) never reaches n_min attacks in a window
(at most 222), so it is not an event and cannot be judged.

**cic2_rf: share of the two events detected (200 draws):**

| Labelling | B | B_ipw | B_ipw_eff | B_ipw_ess |
|---|---|---|---|---|
| random 100% | 100% | 100% | 100% | 100% |
| random 20% | 50% | 50% | 100% | 50% |
| alerts 90%, normal 50% | 94% | 94% | 100% | 94% |
| alerts 90%, normal 20% | 50% | 50% | 100% | 50% |
| alerts 90%, normal 10% | 0% | 42% | 100% | 0% |
| alerts 90%, normal 5% / 2% / 1% | 0% | 0% | 100% | 0% |

No strategy raised a false alarm under any correct-weight condition, for either detector
(median delay 12-14 windows where detected).

**Why the pattern differs from UNSW-NB15.** In these attack-heavy windows (85-99%
attacks) there are only 50-700 normal records per window. The eligibility rule needs
m_min = 500 labelled normal records per cohort (to estimate the false-positive rate), so
labelling fewer normal records leaves the cohorts ineligible and the monitor silent,
already under random 20% labelling for the Portscan event. Weighting the counts before
the check (B_ipw_eff) passes the rule and detects both events at every policy. Because the
detectors make no false positives, the noisy false-positive estimate that caused
B_ipw_eff's false alarms on UNSW-NB15 does no harm here.

**Wrong labelling rates (cic2_hgb, no events, so every alarm is false):** with the
assumed p_normal halved, draws with a false alarm: B_ipw 42% (true policy 0.9/0.1),
B_ipw_eff 92% / 97% (0.9/0.1, 0.9/0.02), **B_ipw_ess 0%**. Doubling the rate or assuming
p_alert 0.7: 0% for all. Same asymmetry as on UNSW-NB15.

**What this adds to Paper 2.**

1. The bias problem is general, but its form depends on the detector: with false
   positives (UNSW-NB15) alert-first labels cause false alarms; without them (CIC-IDS-2017)
   they starve the monitor of labelled normal traffic, and real degradations go unseen.
2. The choice of eligibility rule is a trade-off, not a free win: the effective-sample-size
   rule never false-alarms (both datasets, also with wrong rates) but is silent on CIC
   below 50% normal labelling; the weighted-count rule detects on CIC at every policy but
   false-alarms on UNSW-NB15 and with underestimated rates.
3. Practical reading: the needed audit rate depends on how many normal records a cohort
   holds; in attack-heavy periods the minimum is far above the ~2.5% of section 3.
4. Limitations: one Friday, no held-out CIC test set (D2), Botnet too small to judge,
   cic2_rf is a weak detector (validation recall 0.20); cic2_hgb has no harmful event,
   so on CIC it informs only the false-alarm side.
