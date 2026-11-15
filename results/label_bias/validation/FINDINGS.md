# Findings: label-bias study on February validation (Paper 2)

Run 2026-11-15 on Ali's machine (9.2 minutes). Fixed grid (RESEARCH_DECISIONS.md D17):
32 label conditions x 6 scenarios x 200 streams, label delay 5 windows, frozen
`configs/strategies.toml`. `p_alert` = share of alerts (predicted attacks) that get a
label; `p_normal` = share of records predicted normal that get a label. Numbers from
`policy_table.csv` and `summary.csv`.

## 1. The bias zone: alerts labelled much more often than normal traffic

Uncorrected B (calibrated F1), p_alert 0.9:

| p_normal | False alerts, stable and harmless | Detection, harmful |
|---|---:|---:|
| 0.50 | 0% | 100% |
| 0.20 | 0% | 99% |
| 0.10 | 100% | 11% |
| 0.05 | 100% | 0% |
| 0.02 | 98% | 36% |

- The damage starts when normal traffic is labelled at about 10% or less while alerts are
  labelled at 50-100%. At 20% or more, the bias is too small to trigger the 0.05 rule.
- The same pattern holds for p_alert 1.0, 0.7 and 0.5; the lower p_alert, the later the
  failure sets in (p_alert 0.5: fails only at p_normal 0.05).
- B with plain F1 never false-alarms on stable streams but always on H1 (as with random
  labels), and misses the Fuzzers change (X1) under every biased policy: detection 75%
  pooled = X2 found, X1 missed.

## 2. Weighting (B_ipw) repairs it down to 5% labelling of normal traffic

- With the approved eligibility rule, B_ipw keeps false alerts at 0-1.5% under **every**
  policy, and detects 99-100% of harmful streams for p_normal >= 0.05.
- At p_normal 0.02 detection falls to 68-92% (median delay 8-19 windows), because few
  cohorts reach 500 labelled normal records.
- At p_normal 0.01 **no** cohort is eligible except during a false-positive burst (flagged
  normal records are labelled at p_alert, so the burst itself creates enough labelled
  normals). B, B_F1 and B_ipw then "detect" X2 (100%) and miss X1 (0%) for that reason
  alone: eligibility, not the metric, raises the alarm. This is an artefact to report,
  not a success.

## 3. Eligibility on weighted counts (B_ipw_eff) helps at very low rates, at a cost

- B_ipw_eff keeps detection at 87-89% even at p_normal 0.01 (X1 found in 100% of abrupt
  streams), and 96-97% at 0.02.
- Its false alerts rise to 4-6% at p_normal 0.01-0.02 and to 15-19% at 0.05, almost all
  on H1 (rare attacks): weighted counts pass the eligibility rule while very few missed
  attacks are actually labelled, so recall estimates are noisy.
- A variance-aware rule (for example Kish's effective sample size of the weighted counts)
  is the principled next step; it would need its own fixed decision before the test run.

## 4. Wrong weights: assuming too small a labelling rate is the dangerous error

At true (0.9, 0.1):

| Assumed | B_ipw false alerts | B_ipw detection |
|---|---:|---:|
| correct | 1.5% | 100% |
| p_normal halved (0.05) | 28% | 94% |
| p_normal doubled (0.2) | 0% | 100% |
| p_alert 0.7 instead of 0.9 | 1% | 100% |

- Underestimating how often normal traffic is labelled over-weights it, underestimates
  FPR and recall, and causes false alarms (28-39%). Overestimating is nearly harmless at
  10% (it only under-corrects), but costs detection at the 2% audit rate (B_ipw 78%).
- Practical rule: when the labelling rate of normal traffic is uncertain, err high.

## Messages for Paper 2

1. Alert-first labelling breaks performance monitoring when normal traffic is labelled at
   10% or less, in both directions: calibrated F1 floods with false alarms, plain F1
   silently misses attacks.
2. Inverse-probability weighting with known rates repairs it down to 5% labelling of
   normal traffic, with no tuning.
3. Below that (audit sampling of 1-2%), the eligibility rule decides the outcome; weighted
   eligibility recovers detection but adds false alarms, and a variance-aware rule is
   needed.
4. Wrong rates are asymmetric: underestimating the audit rate is the costly mistake.
