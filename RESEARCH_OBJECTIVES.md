# Research Objectives and Questions

## 1. Main Research Aim

The aim of this research is to develop and experimentally evaluate methods for detecting genuine performance degradation in network anomaly detection systems under changing traffic conditions and delayed or partially available ground-truth labels.

The research compares three monitoring approaches:

- Input-distribution monitoring.
- Delayed performance-based monitoring.
- Combined input-warning and performance-confirmation monitoring.

The central concern is whether these approaches can distinguish harmless traffic changes from changes that genuinely reduce anomaly detection performance.

## 2. Main Research Question

How do input-distribution monitoring, delayed performance-based monitoring, and combined monitoring compare in detecting genuine network anomaly-detection performance degradation under controlled traffic changes and delayed or partially available ground-truth labels?

## 3. Specific Research Questions

### RQ1 — Input-Distribution Monitoring

How effectively can input-distribution monitoring identify changes in network traffic without access to ground-truth labels?

Investigations:

- Detection of numerical feature distribution changes.
- Detection of categorical feature distribution changes.
- Effects of multiple statistical tests.
- Effects of the combined-feature warning threshold.
- False warnings under stable and harmless-shift conditions.

### RQ2 — Performance-Based Monitoring

How effectively can delayed performance-based monitoring identify genuine anomaly detection performance degradation when only some ground-truth labels are available?

Investigations:

- F1-score degradation.
- Delayed label availability.
- Partial label availability.
- Minimum labelled sample requirements.
- Detection delay and missed degradation events.

### RQ3 — Combined Monitoring

Does combining input-distribution warnings with delayed performance confirmation provide useful information compared with using either monitoring approach independently?

Investigations:

- Whether distribution warnings precede genuine degradation.
- Whether performance degradation can be detected without an earlier distribution warning.
- Number of unconfirmed distribution warnings.
- Warning lead time.
- Detection performance compared with Strategies A and B.

### RQ4 — Robustness to Delayed and Partial Labels

How do different label delays and label availability rates affect the reliability and timeliness of the monitoring approaches?

Initial experimental conditions:

- Label delays: 0, 5, and 10 windows.
- Label availability: 100%, 50%, and 20%.

### RQ5 — Reliability of Evaluation

How can genuine performance degradation be distinguished from ordinary traffic variation, and how reliably can the monitoring methods be evaluated under controlled conditions?

Investigations:

- Stable traffic and stable performance.
- Harmless distribution shifts.
- Harmful distribution shifts.
- Reproducibility across experimental repetitions.
- Uncertainty in measured evaluation metrics.

## 4. Research Objectives

### Objective 1 — Establish a Reproducible Baseline

Prepare and validate a network anomaly detection baseline using UNSW-NB15.

Expected outputs:

- Audited dataset.
- Chronological data partitions.
- Documented feature selection.
- Trained baseline classifier.
- Overall and window-level performance metrics.

### Objective 2 — Investigate Traffic Distribution Changes

Develop an input-distribution monitoring approach that does not depend on ground-truth labels.

Expected outputs:

- Numerical feature monitoring.
- Categorical feature monitoring.
- Multiple-testing correction.
- Combined-feature warning mechanism.

### Objective 3 — Develop Delayed Performance Monitoring

Develop a monitoring approach that measures actual classifier performance using only labels available at the monitoring time.

Expected outputs:

- Prediction and label association.
- Label-delay simulation.
- Partial-label simulation.
- F1-based degradation detection.
- Insufficient-label handling.

### Objective 4 — Develop Combined Monitoring

Combine input-distribution warnings and delayed performance confirmation while retaining an independent performance-detection path.

Expected outputs:

- Monitoring state transitions.
- Provisional warnings.
- Performance-based confirmation.
- Unconfirmed-warning records.
- Warning lead-time measurements.

### Objective 5 — Design Controlled Experiments

Evaluate the approaches under different traffic and performance conditions.

Expected outputs:

- Stable scenario.
- Harmless-shift scenario.
- Harmful-shift scenario.
- Delayed-label scenarios.
- Partially available-label scenarios.

### Objective 6 — Compare and Interpret Results

Compare the three monitoring strategies using consistent evaluation rules.

Expected outputs:

- Event recall.
- Alert precision.
- False alerts.
- Detection delay.
- Missed degradation events.
- Warning lead time.
- Computational overhead.
- Repeated-experiment results and uncertainty estimates.

## 5. Operational Definition of Genuine Performance Degradation

The initial operational definition uses F1-score.

Let:

- F1_reference represent the fixed reference F1-score.
- F1_current represent the F1-score of an eligible evaluation window.
- Delta represent the absolute degradation threshold.

The provisional degradation boundary is:

F1_current <= F1_reference - 0.05

A degradation event is confirmed when the threshold is crossed in two consecutive eligible evaluation windows.

Important conditions:

1. The reference period must be justified using validation evidence.
2. Only labels released by the monitoring time may be used.
3. A window with insufficient labelled examples is ineligible.
4. An ineligible window must not be interpreted as evidence of stable performance.
5. The 0.05 threshold is an operational choice, not a statistical significance claim.
6. Sensitivity analysis will examine thresholds of 0.03 and 0.10.

The reference period has not yet been finalized.

## 6. Comparison Framework

The three approaches will be evaluated under the same experimental conditions.

| Property | Strategy A | Strategy B | Strategy C |
|---|---|---|---|
| Input distribution | Yes | No | Yes |
| Ground-truth labels | No | Yes | Yes, for confirmation |
| Delayed labels | Not required | Required | Required for confirmation |
| Early warning | Yes | Not necessarily | Yes |
| Performance confirmation | No | Yes | Yes |
| Can identify harmless input shifts? | Detects the shift, not its harmlessness | Can assess performance if labels are available | Can distinguish warning from confirmed degradation |

The comparison must not assume that the combined approach is automatically superior.

## 7. Research Evaluation Criteria

The primary evaluation criteria are:

1. Event recall.
2. Alert precision.
3. False alerts.
4. Detection delay.
5. Missed degradation events.
6. Warning lead time.

Additional criteria include:

- Unconfirmed warnings.
- Input-distribution detection results.
- Performance-confirmation delay.
- Computational overhead.

Evaluation rules for event matching, repeated alerts, and warning association must be defined before the final experiments.

## 8. Research Scope

Included:

- Binary network anomaly detection.
- UNSW-NB15 as the initial experimental dataset.
- Frozen baseline classifier.
- Input-distribution monitoring.
- Delayed performance-based monitoring.
- Combined monitoring.
- Controlled traffic changes.
- Delayed and partially available labels.
- Reproducible software tests and research experiments.

Not assumed or claimed:

- That every traffic distribution shift causes performance degradation.
- That every detected distribution shift is harmful.
- That combined monitoring must outperform individual approaches.
- That results on UNSW-NB15 automatically generalize to every operational network.
- That the proposed combination is novel without further literature investigation.

## 9. Expected Research Contribution

The intended contribution is an experimental comparison of input-distribution monitoring, delayed performance-based monitoring, and combined monitoring under controlled harmless and harmful network traffic changes.

The evaluation will define genuine degradation using measured classifier performance and investigate how delayed or partially available ground-truth labels affect monitoring reliability.

The novelty and significance of this contribution must be established through the literature review and experimental results.

## 10. Current Research Status

The initial Random Forest baseline has been trained and evaluated on the validation partition.

The dataset audit, chronological split, initial feature selection, and baseline results have been documented in PROJECT_CONTEXT.md.

The validation-window attack-category composition audit remains an important next step.

The stable reference period and final monitoring thresholds must not be treated as finalized until supported by validation evidence.

