# Research Decisions and Methodological Record

This document records approved methodological decisions, provisional choices, and unresolved questions.

Decisions should only be changed when supported by research evidence or an explicitly documented methodological revision.

## 1. Research Design

The research compares three monitoring strategies:

- Strategy A: Input-distribution monitoring.
- Strategy B: Delayed performance-based monitoring.
- Strategy C: Combined input warning and performance confirmation.

The central distinction is:

Input-distribution change does not necessarily imply anomaly detector performance degradation.

Genuine degradation must be established using measured classifier performance against ground-truth labels.

## 2. Baseline Classifier

Initial baseline:

- Algorithm: Random Forest.
- Number of trees: 200.
- Class weighting: balanced.
- Random seed: 42.
- Parallel processing: n_jobs = -1.
- Classification threshold: 0.5.

The classifier is initially frozen during monitoring experiments.

Any future adaptation experiment must be separately designed and documented.

## 3. Performance Degradation Definition

Primary metric: F1-score.

Initial operational rule:

A window indicates degradation when:

F1_current <= F1_reference - 0.05

Confirmation requires the condition to hold for two consecutive eligible evaluation windows.

Additional rules:

- Reference F1 must be established from a justified stable validation period.
- Only labels released by the current monitoring time may be used.
- Insufficiently labelled windows are ineligible.
- Ineligible windows must not be interpreted as evidence of stable performance.
- The 0.05 threshold is an operational threshold, not a statistical significance claim.

Planned sensitivity analysis:

- Absolute F1 reduction of 0.03.
- Absolute F1 reduction of 0.05.
- Absolute F1 reduction of 0.10.

**Status:** The operational rule is approved provisionally. The reference period and minimum labelled sample requirement remain unresolved.

**Changed 2026-11-12 (see section 16, D5):** the primary monitored metric for Strategy B
is now calibrated F1; plain F1 remains as a comparison variant. The 0.05 threshold and
the two-window rule are unchanged; the reference period (D6) and the minimum labelled
sample (D8) are now resolved.

## 4. Strategy A — Input-Distribution Monitoring

### Numerical Features

Use the Kolmogorov-Smirnov test for numerical feature distribution comparisons.

### Categorical Features

Use the chi-square test or another justified categorical distribution test.

Do not apply the Kolmogorov-Smirnov test to categorical features.

### Multiple Testing

Apply Benjamini-Hochberg correction to account for multiple feature-level statistical tests.

Initial candidate significance threshold:

0.01

### Combined-Feature Warning

**Selected primary approach: Combined-feature warning.**

Raise a distribution warning when a validation-calibrated minimum proportion of monitored features demonstrate statistically significant changes after multiple-testing correction.

Individual-feature warnings should also be retained for later analysis and ablation.

The combined-feature threshold must be selected using validation data, not test data.

A Strategy A warning means that the observed input distribution has changed. It does not establish that detection performance has degraded.

Additional concerns:

- High-cardinality categorical features.
- Sparse categories.
- Multiple-testing effects.
- Sensitivity to window size.
- Statistical significance versus practical significance.

**Status:** Primary design selected. Calibration and implementation remain pending.

## 5. Strategy B — Delayed Performance-Based Monitoring

Use stored classifier predictions matched to their original flow or evaluation-window identifiers.

Ground-truth labels must be used only after their simulated release.

Primary monitoring signal:

F1-score calculated from available labelled prediction cohorts.

Rules:

- Maintain a fixed reference F1.
- Apply the provisional 0.05 absolute reduction threshold.
- Require two consecutive eligible windows.
- Mark insufficiently labelled windows as ineligible.
- Do not treat missing labels as evidence of stable performance.

### Label Delay and Availability

Initial experiment grid:

| Label Delay | Label Availability |
|---|---|
| 0 windows | 100%, 50%, 20% |
| 5 windows | 100%, 50%, 20% |
| 10 windows | 100%, 50%, 20% |

This produces nine initial combinations.

Partial availability will initially be simulated through reproducible random selection independent of class and prediction.

This is a simplifying assumption. Biased or class-dependent label availability must be discussed as a limitation and potential future experiment.

### ADWIN

ADWIN is retained as a possible later comparison.

A change in error rate detected by ADWIN is not equivalent to a confirmed F1 degradation event.

It must not replace the primary F1-based operational definition.

### Important Implementation Requirement

Predictions must retain identifiers and timestamps so that delayed labels can be matched to the correct original observations or evaluation cohorts.

Labels must not be assigned to whichever window happens to receive them.

### Minimum Labelled Sample Size

A minimum sample requirement must be established before a window is eligible for F1 evaluation.

The requirement should consider:

- Number of labelled observations.
- Presence of both classes.
- Reliability and stability of the F1 estimate.

**Status:** Monitoring concept and initial experiment grid approved. Minimum sample size and detailed label-release mechanics remain pending.

## 6. Strategy C — Combined Monitoring

The combined strategy uses input-distribution warnings and delayed performance confirmation.

Initial states:

1. Normal.
2. Provisional warning.
3. Confirmed degradation.
4. Unconfirmed warning.

### Warning Path

Strategy A can raise a provisional warning when its combined-feature threshold is crossed.

### Confirmation Path

Strategy B confirms genuine performance degradation using the approved F1-based rule.

### Independent Confirmation

A direct performance-confirmation path must remain available even when Strategy A has not raised a warning.

This prevents the combined strategy from missing degradation simply because the input monitor did not issue a warning.

### Warning Association

A later performance-confirmed degradation may be associated with an earlier input warning only within a predefined warning association period.

The association period must be calibrated using validation data.

### Required Event Categories

Record separately:

1. Degradation preceded by an input warning.
2. Degradation detected by performance monitoring without an earlier input warning.
3. Input-distribution warning never confirmed as performance degradation.

Report warning lead time and unconfirmed warnings.

The combined strategy must be evaluated experimentally rather than assumed to be superior.

**Status:** Architecture approved. Warning association period and implementation remain pending.

## 7. Dataset Decisions

Dataset: UNSW-NB15.

Data location: set per machine in `configs/paths.toml` (development machine: `E:\UNSW-Dataset Original`).

Working repository: `network-anomaly-performance-monitoring` on GitHub.

Rules:

- Never modify original raw CSV files.
- Preserve the original 49-column mapping.
- Treat January and February capture sessions separately.
- Use chronological ordering for the February experimental split.
- Preserve the frozen training, validation, and test boundaries.
- Fit preprocessing only on training data.
- Do not use test labels during monitoring calibration.

February split:

| Partition | Records |
|---|---:|
| Training | 726,426 |
| Validation | 290,575 |
| Testing | 435,843 |

## 8. Feature Selection Decisions

Initial baseline feature set:

23 numerical features:

sport, dsport, dur, sbytes, dbytes, sttl, dttl, sloss, dloss, Sload, Dload, Spkts, Dpkts, swin, dwin, trans_depth, res_bdy_len, Sjit, Djit, Sintpkt, Dintpkt, synack, ackdat.

3 categorical features:

proto, state, service.

Target:

Label.

The attack_cat column is excluded.

### Excluded Features

The following features are excluded from the initial baseline for the stated reasons:

- srcip and dstip: identity memorization risk.
- stcpb and dtcpb: high cardinality and connection-specific information.
- smeansz and dmeansz: deterministic relationships with byte and packet counts where defined.
- Stime and Ltime: chronology information rather than initial model inputs.
- tcprtt: exactly equal to synack + ackdat in the audited records.
- is_sm_ips_ports: deterministic transformation of IP and port information.
- ct_state_ttl: strong label association and unresolved construction provenance.
- ct_flw_http_mthd, is_ftp_login, ct_ftp_cmd: missingness, file-dependent behaviour, or unexpected values.
- ct_* features from indices 40 to 46: construction semantics and temporal information concerns.
- attack_cat: target-related information.

These are initial conservative decisions. Appropriate feature ablation experiments may revisit them.

### Destination Port Conversion

The dsport feature contains 241 hexadecimal values represented as:

0xcc09

These values represent decimal port 52233.

The model pipeline must convert hexadecimal and decimal representations correctly.

**Extension (2026-11-08, January session).** The January session contains values the
February session does not: `sport` has 6 hexadecimal values (`0x000c` x4, `0x000b` x2),
and 9 port values are `-` (2 in `sport`, 7 in `dsport`), meaning no port (e.g. ICMP or
ARP traffic). Decisions:

- `sport` uses the same decimal/hexadecimal conversion as `dsport`.
- `-` is encoded as -1, which cannot be a real port. This keeps every record, so the
  January split and windows are unchanged. Dropping the records or keeping them as
  missing values were the alternatives considered.
- Any other non-numeric port value still stops preprocessing.

February contains no `-` ports and no hexadecimal `sport` values, so February features,
the baseline and `feb_hgb` are unaffected.

Original raw CSV files must remain unchanged.

## 9. Validation and Test Separation

Training data is used to fit the baseline classifier and preprocessing.

Validation data is used to:

- Calibrate monitoring thresholds.
- Investigate the stable reference period.
- Select minimum labelled sample requirements.
- Calibrate warning association periods.
- Select other monitoring parameters.

Test data is reserved for final evaluation.

Test results must not be used to tune thresholds or modify the monitoring methodology.

## 10. Evaluation Decisions

The six primary metrics are:

1. Event recall.
2. Alert precision.
3. False alerts.
4. Detection delay.
5. Missed degradation events.
6. Warning lead time.

Additional reporting:

- Unconfirmed warnings.
- Input-distribution detection results.
- Performance-confirmation delay.
- Computational overhead.

Report detection delay in windows and elapsed time.

Event matching, repeated-alert counting, and warning association rules must be formally specified before final evaluation.

Experiments should use reproducible seeds and repeated runs where appropriate.

Confidence intervals or other suitable uncertainty estimates should accompany important comparisons.

## 11. Controlled Scenario Requirements

The research must include:

### Stable Scenario

Traffic distribution and detector performance remain stable.

Purpose: Measure false alarms.

### Harmless Shift Scenario

Input distribution changes without genuine performance degradation.

Purpose: Test whether distribution warnings are incorrectly interpreted as harmful degradation.

### Harmful Shift Scenario

A controlled traffic change causes measurable detector performance degradation.

Purpose: Evaluate genuine degradation detection.

### Delayed and Partial Label Scenarios

Repeat relevant experiments using the planned delay and label-availability combinations.

Natural traffic variation must not automatically be treated as a verified harmless or harmful event.

Controlled experiments must establish known event conditions.

## 12. Unresolved Methodological Questions

The following questions remain open:

1. Which validation windows provide a defensible stable reference period?
2. What minimum number of labelled observations is required for eligible F1 evaluation?
3. How should high-cardinality and sparse categorical features be monitored?
4. What minimum proportion of changed features should raise a Strategy A warning?
5. What warning association period should Strategy C use?
6. How should repeated alerts be counted?
7. How should overlapping or adjacent degradation events be matched?
8. How should biased or class-dependent label availability be investigated?
9. What statistical method is most appropriate for comparing repeated experimental results?
10. How can controlled harmless and harmful traffic changes be constructed without introducing unintended confounding factors?

## 13. Robustness Runs (added 2026-11-08)

To test whether the attack-share findings generalise beyond one model and one capture
day, the same analysis is repeated on additional runs. These do not replace the
February Random Forest baseline or its frozen split.

**January split.** The January 22-23 session is split on its own with the February
rule: chronological, first 50% training, next 20% validation, last 30% test, each
boundary moved forward to the end of its timestamp group. Records outside both
sessions stop the run. The January test partition is never loaded. Implemented in
`src/nadmon/sessions.py`.

**January has no attacks in its default validation partition (2026-11-08).** With the
50/20/30 rule, January's training partition has 4.09% attacks and its validation
partition (217,442 records) has none, so detection performance cannot be measured there.
Decision (approved 2026-11-08): January becomes a **replication-only session with no
held-out test**. Its whole attack timeline, including the last 30%, may be inspected
(`scripts/describe_session.py`) to choose a split with attacks in both training and
validation; that split will be recorded here before use. February's test partition stays
unseen. `train_model.py` now stops if any partition has fewer than 100 attacks.

**January split (approved 2026-11-08).** The January timeline
(`results/sessions/jan/`) shows all 22,215 January attacks (2.04% of the session) in a
two-hour burst, 11:49-13:49 UTC, covering the first 38 of 218 windows; the remaining
traffic contains no attacks. Rule `attack_period_50_50`:

- Attack period: from the session start to the end of the timestamp group of the last
  attack.
- Training: the first 50% of the attack period's records; validation: the rest. Both
  boundaries at timestamp-group ends.
- Attack-free traffic after the attack period is not used. There is no January test set.

Alternatives considered: a 40/60 split (more validation windows, weaker model) and
extending validation into the attack-free traffic (mixes a second question into the
run). Expected size: about 95,000 training records and about 19 validation windows, so
the first-10-window reference leaves about 9 monitored windows and the per-period
Fuzzers analysis is skipped. January results are therefore a smaller, supporting
replication, not a second primary experiment.

**Second model.** Histogram gradient boosting (`src/nadmon/models.py`): 200 iterations,
learning rate 0.1, early stopping off, balanced class weights, native categorical
handling, random state 42. Settings are fixed in advance and not tuned on validation
data, matching the Random Forest's treatment.

**Runs.** `feb_hgb`, `jan_rf`, `jan_hgb` (`scripts/train_model.py`), each analysed with
`scripts/analyze_attack_share.py --run <name>` and compared with
`scripts/compare_runs.py`. The analysis settings (window size 5,000, low-share split
12%, Strategy B rule, first-10-window reference, resampling seed) are identical across
runs.

## 14. Second Dataset: Improved CIC-IDS-2017 (added 2026-11-09)

**Data.** The improved CIC-IDS-2017 of Engelen et al. (2021), in the IEEE CNS 2022
version by Liu et al. (five day files, Monday-Friday, 2,099,976 flows, 91 columns),
profiled in `results/cicids2017_profile/`. Each attack type runs in its own 1-2 hour
block and each day introduces new attack types, so the within-window category-mix
analysis of UNSW-NB15 does not carry over directly. CIC-IDS-2017 instead tests whether
monitoring separates real degradation (unseen attack types) from harmless change
(attacks stopping).

**Decisions (approved 2026-11-09).**

- **Split:** train on Monday-Thursday (time-sorted), monitor Friday (time-sorted).
  Friday contains Portscan (similar to Thursday's Infiltration-Portscan), DDoS (related
  to Wednesday's DoS), Botnet (unseen) and long attack-free stretches. No test set is
  held out. Alternative considered: train Monday-Wednesday, monitor Thursday-Friday.
- **Attempted flows** (failed attack connections, 12,926 flows) are labelled BENIGN,
  as in the dataset authors' own benchmark (Engelen et al. 2021). Alternatives
  considered: excluding them, or labelling them as attacks.
- **Invalid values:** the 8 rows with infinite `Flow Bytes/s` or `Flow Packets/s` are
  dropped; negative header lengths (about 790 rows) are kept as recorded.
- **Features** (consistent with the UNSW-NB15 decisions): identifiers (`id`, `Flow ID`,
  `Src IP`, `Dst IP`, `Timestamp`) are excluded; ports are kept; `Protocol` is
  categorical; all other columns are numeric features. The port ablation in TODO
  applies to both datasets.
- **Timestamps** carry no time zone; they are used as given.
- **Models:** the same Random Forest and gradient boosting settings as for UNSW-NB15.

**Undefined window metrics.** Windows without attacks make recall, balanced accuracy
and MCC undefined. They are recorded as NaN and treated as ineligible: the Strategy B
rule skips them (they neither count towards nor break a run of drops). F1 is 0 in a
window with no attacks but at least one false positive, and NaN only when it is 0/0.
UNSW-NB15 results are unchanged by this rule because every UNSW-NB15 window contains
attacks.

## 15. Decision Change Policy

When a methodological decision changes:

1. Record the original decision.
2. Explain why the change is necessary.
3. Record supporting experimental or literature evidence.
4. Update the relevant implementation and tests.
5. Record the change in CHANGELOG.md.
6. Preserve the ability to reproduce earlier experiments where possible.

Do not silently change research thresholds, dataset splits, feature definitions, or event-matching rules.

## 16. Strategy Design Decisions (approved 2026-11-12)

All decisions D1-D14 of `STRATEGY_DESIGN_SPEC.md` were approved by Ali on 2026-11-12. The
spec holds the full text and evidence; the essentials:

| # | Decision |
|---|---|
| D1 | Calibrate every threshold on February validation; evaluate once on February test, after all calibrated values are frozen in `configs/strategies.toml` |
| D2 | New CIC-IDS-2017 runs `cic2_rf`, `cic2_hgb`: train Monday-Wednesday plus the first 50% of Thursday, validate on the last 50% of Thursday, monitor Friday; Paper 1 runs unchanged |
| D3 | Scenarios S0, H1-H3, X1-X2 built by resampling real records from strata (attack category; benign `service|proto|state`); 40 windows, onset at window 21 |
| D4 | Ground truth from expected calibrated F1: harmful if it falls by at least 0.10; harmless if it changes by less than 0.02 and the stratum mix moves by at least 0.10 (total variation) |
| D5 | Strategy B monitors calibrated F1 (reference share = pooled validation share); plain F1 kept as variant B-F1 |
| D6 | B reference = pooled calibrated F1 over all validation windows, fixed before monitoring |
| D7 | Labels released at the end of window w + d (d = 0, 5, 10); availability 100/50/20% independent of class; plus one alert-first condition (0.9 / 0.1) |
| D8 | Eligible cohort: at least n_min labelled attacks (n_min = ceil(2.326^2 r(1-r)/0.05^2); 68 for feb_rf) and 500 labelled normal records; short cohorts pooled with later windows up to 5 windows |
| D9 | B alarm: drop of at least 0.05 below the reference in 2 consecutive eligible cohorts |
| D10 | Strategy A: KS (numeric), chi-square with sparse categories merged (categorical), Benjamini-Hochberg at 0.01; warn when a proportion q of features changed in 2 consecutive windows; q calibrated for at most 5% false warnings on S0 validation streams |
| D11 | Strategy C in two variants: passive (labels A warnings as confirmed or not) and active (during a warning, B confirms on one flagged cohort); association period L = d + 5, then calibrated on validation harmful scenarios (95% of warning-to-confirmation gaps) |
| D12 | One event per controlled stream; alarm state with re-arm after 2 unflagged eligible cohorts; true alert = alarm after onset on a harmful scenario |
| D13 | 200 streams per scenario and condition, paired across strategies; Wilson intervals, bootstrap intervals for delays, McNemar and Wilcoxon tests |
| D14 | Grid: 6 UNSW-NB15 scenarios plus natural CIC Friday; 9 + 1 label conditions; strategies A, B-F1, B, C-passive, C-active; models feb_rf (primary), feb_hgb, cic2_rf, cic2_hgb |

**Change record for D5 (section 15 policy).**
1. Original decision (section 3): primary metric F1.
2. Reason: window F1 depends on the attack share, so an F1-based rule raises alarms when
   only the share changes; under D4, scenario H1 would be "degraded" by F1 although the
   model is unchanged.
3. Evidence: Paper 1 simulation (`results/robustness_summary.md`, calibrated F1 section):
   at 1% attacks, plain F1 false-alarms in 100% of UNSW-NB15 streams, calibrated F1 in
   0-0.5%; calibrated F1 still flags both January false-positive bursts.
4. Implementation and tests: `nadmon.attack_share.calibrated_f1`, `nadmon.strategies`.
5. Recorded in CHANGELOG.md.
6. Reproducibility: plain F1 remains available as variant B-F1.

**Additions approved 2026-11-12 after the full validation run** (`results/strategies/validation/FINDINGS.md`):

| # | Addition |
|---|---|
| D15 | Variant B_ipw: Strategy B on inverse-probability-weighted cohort counts, using the known labelling probabilities of each condition (alert-first: 0.9 for predicted attacks, 0.1 for predicted normal). Motivation: under alert-first labels, B false-alarmed on every stable stream and missed most harmful changes |
| D16 | Variant A_natural (and C_active_natural): Strategy A's threshold set on the real time-ordered validation windows (at most 5% of windows flagged) instead of resampled stable streams. Motivation: as calibrated (q = 0.038), A flagged 100% of real validation windows |

