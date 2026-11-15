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
