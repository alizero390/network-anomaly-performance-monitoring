# Project Context

## 1. Project Overview

**Working Title:**

Development and Evaluation of Methods for Detecting Network Anomaly Detection Performance Degradation Under Delayed Ground-Truth Feedback.

**Academic Context:**

Master's research project at the Higher School of Economics (HSE), Moscow.

**Primary Research Area:**

Network anomaly detection, machine learning model monitoring, concept drift, performance degradation, and delayed ground-truth feedback.

## 2. Research Motivation

Network traffic changes over time. A machine learning anomaly detector may encounter traffic patterns that differ from those observed during training.

However, a change in traffic distribution does not necessarily mean that the detector has become less effective.

This research distinguishes between:

1. Input-distribution changes that do not reduce detection performance.
2. Changes that cause genuine degradation in anomaly detection performance.
3. Situations where performance degradation cannot be identified immediately because ground-truth labels are delayed or only partially available.

The research investigates how monitoring methods can identify genuine performance degradation while controlling false warnings.

## 3. Main Research Question

How do input-distribution monitoring, delayed performance-based monitoring, and combined monitoring compare in detecting genuine network anomaly-detection performance degradation under controlled traffic changes and delayed or partially available ground-truth labels?

## 4. Research Objectives

1. Establish a reproducible network anomaly detection baseline.
2. Investigate traffic-distribution changes independently of actual model performance.
3. Develop an input-distribution monitoring strategy.
4. Develop a performance-based monitoring strategy that uses only labels available at the time of monitoring.
5. Develop a combined warning-and-confirmation strategy.
6. Evaluate all three strategies under stable, harmless-shift, and harmful-shift conditions.
7. Investigate the effects of delayed and partially available ground-truth labels.
8. Compare detection capability, false alerts, detection delay, and computational overhead.

## 5. Core Research Principle

A traffic-distribution shift must not automatically be treated as model performance degradation.

Genuine degradation is determined using the detector's measured performance against ground-truth labels.

The monitoring strategies must therefore be evaluated against actual performance degradation events rather than assuming that every injected or observed distribution change represents a harmful event.

## 6. Dataset

**Dataset:** UNSW-NB15.

**Dataset location:** set per machine in `configs/paths.toml` (development machine: `E:\UNSW-Dataset Original`).

**Working repository:** `network-anomaly-performance-monitoring` on GitHub (previously `E:\UNSW-Thesis`).

The original dataset must remain unchanged.

### Raw Dataset Files

- UNSW-NB15_1.csv
- UNSW-NB15_2.csv
- UNSW-NB15_3.csv
- UNSW-NB15_4.csv

The four files contain 2,540,047 records in total.

The CSV files have no headers and contain 49 columns.

The original data includes two separate capture periods:

- January 22–23, 2015.
- February 18, 2015.

These sessions must not be treated as one continuous uninterrupted traffic stream.

### February Chronological Split

The February session contains 1,452,844 records.

The frozen chronological split is:

| Partition | Records |
|---|---:|
| Training | 726,426 |
| Validation | 290,575 |
| Testing | 435,843 |
| Total | 1,452,844 |

The split boundaries were checked to ensure that timestamp groups were not divided between partitions.

## 7. Initial Feature Selection

The provisional baseline uses 26 input features:

- 23 numerical features.
- 3 categorical features.

### Numerical Features

sport, dsport, dur, sbytes, dbytes, sttl, dttl, sloss, dloss, Sload, Dload, Spkts, Dpkts, swin, dwin, trans_depth, res_bdy_len, Sjit, Djit, Sintpkt, Dintpkt, synack, ackdat.

### Categorical Features

proto, state, service.

### Target

Label.

The attack_cat column is excluded because it contains attack-category information derived from the target classification.

Feature selection remains provisional and may be investigated through later ablation experiments.

## 8. Baseline Model

**Model:** Random Forest Classifier.

Configuration:

- 200 trees.
- class_weight = balanced.
- random_state = 42.
- n_jobs = -1.
- Default classification threshold = 0.5.

Preprocessing:

- Numerical features are processed as numerical values.
- Categorical features are one-hot encoded.
- Unknown categorical values are handled using handle_unknown = ignore.
- Preprocessing is fitted using training data only.

### Baseline Results

Validation results:

| Metric | Value |
|---|---:|
| Accuracy | 0.98929 |
| Precision | 0.977826 |
| Recall | 0.967868 |
| F1-score | 0.972821 |
| False Positive Rate | 0.00542 |

Confusion matrix:

| | Predicted Normal | Predicted Attack |
|---|---:|---:|
| Actual Normal | 231,768 | 1,263 |
| Actual Attack | 1,849 | 55,695 |

The validation dataset contains 58 complete windows of 5,000 records, with an additional 575 records.

Window-level F1 varies considerably despite the high overall F1-score. This makes window-level monitoring an important part of the research.

The first ten windows are only candidate reference windows. They have not yet been approved as the stable reference period.

Attack-category composition and traffic characteristics must be investigated before fixing the reference performance.

## 9. Monitoring Strategies

The research compares three strategies.

### Strategy A — Input-Distribution Monitoring

Purpose:

Identify changes in input traffic without requiring ground-truth labels.

Initial methodology:

- Kolmogorov-Smirnov test for numerical features.
- Chi-square or an appropriate categorical distribution test for categorical features.
- Benjamini-Hochberg correction for multiple testing.
- Initial candidate significance threshold: 0.01.
- Combined-feature warning based on a minimum proportion of monitored features showing significant changes.

A distribution warning does not confirm performance degradation.

The combined-feature warning threshold must be calibrated using validation data.

Individual-feature warnings will remain available for later ablation experiments.

### Strategy B — Delayed Performance-Based Monitoring

Purpose:

Identify genuine degradation using only ground-truth labels that have become available.

Primary metric:

F1-score.

Provisional degradation definition:

- A fixed stable reference F1-score.
- An absolute F1 reduction of at least 0.05.
- The reduction persists for two consecutive eligible evaluation windows.
- Only labels released by the monitoring time may be used.
- Windows with insufficient labelled examples are ineligible.

The threshold of 0.05 is an operational threshold, not a statistical significance claim.

Sensitivity analysis will examine thresholds of 0.03 and 0.10.

Initial label-delay and availability scenarios:

| Label Delay | Label Availability |
|---|---|
| 0 windows | 100%, 50%, 20% |
| 5 windows | 100%, 50%, 20% |
| 10 windows | 100%, 50%, 20% |

Partial label availability will initially be simulated using reproducible random selection independent of class and prediction.

The assumption and its limitations must be documented.

### Strategy C — Combined Monitoring

Purpose:

Combine early distribution warnings with delayed performance confirmation.

Monitoring states:

1. Normal.
2. Provisional warning.
3. Confirmed degradation.
4. Unconfirmed warning.

Strategy A can raise a provisional warning.

Strategy B confirms genuine degradation using the F1-based definition.

A direct performance-confirmation path must remain available even if Strategy A did not raise a warning. This prevents Strategy C from depending entirely on input-distribution detection.

The evaluation will distinguish:

- Degradation preceded by an input warning.
- Degradation detected through performance monitoring without an earlier input warning.
- Distribution warnings that are never confirmed as degradation.

The combined strategy must be evaluated objectively. It must not be assumed to outperform the individual strategies.

## 10. Evaluation Scenarios

Four main scenarios are planned.

### Scenario 1 — Stable Traffic

Traffic distribution and model performance remain stable.

Purpose: Measure false alarms.

### Scenario 2 — Harmless Distribution Shift

Input traffic changes, but detection performance remains stable.

Purpose: Determine whether monitoring methods can distinguish traffic changes from genuine degradation.

### Scenario 3 — Harmful Distribution Shift

A controlled traffic change causes genuine model performance degradation.

Purpose: Evaluate detection of actual performance deterioration.

### Scenario 4 — Delayed and Partially Available Labels

Repeat relevant experiments under different label delays and availability rates.

Purpose: Investigate how delayed feedback affects performance-based monitoring and combined monitoring.

## 11. Evaluation Metrics

Primary evaluation metrics:

1. Event recall.
2. Alert precision.
3. Number of false alerts.
4. Detection delay.
5. Number of missed degradation events.
6. Warning lead time.

Additional reporting:

- Number of unconfirmed warnings.
- Input-distribution change detection results.
- Performance-confirmation delay.
- Computational overhead.

Detection delay should be reported in both evaluation windows and elapsed time.

Event-matching and repeated-alert counting rules must be formally defined before the final experiments.

## 12. Important Methodological Safeguards

- The classifier must remain frozen during monitoring experiments unless a separate adaptation experiment is explicitly designed.
- Training and validation data are used for fitting and calibration.
- Test labels must remain hidden until their simulated release time.
- Thresholds must not be tuned on test data.
- Experiments must be reproducible using fixed random seeds.
- January and February capture sessions must be treated separately.
- Natural dataset changes must not automatically be classified as verified harmless or harmful events.
- Controlled scenarios are required to establish known performance-degradation events.
- Results should include uncertainty estimates and comparisons across repeated experiments.

## 13. Current Project Progress

Completed:

- Original dataset structure inspected.
- Raw CSV column mapping established.
- Dataset chronology audited.
- January and February capture sessions identified.
- February chronological training, validation, and testing partitions established.
- Initial feature audit completed.
- Numerical and categorical feature conversion checked.
- Destination-port hexadecimal values investigated and handled in the model pipeline.
- Initial Random Forest baseline trained.
- Validation predictions and window-level metrics generated.
- Baseline summary saved.
- Git initialized locally.
- Main branch established.
- GitHub private repository created.

### Current Baseline Files

scripts/baseline.py

models/random_forest_baseline.joblib

results/baseline_summary.json

results/validation_predictions.csv

results/validation_window_metrics.csv

The model and prediction file are generated outputs and are excluded from Git initially.

## 14. Immediate Next Research Tasks

1. Audit attack-category composition across validation windows.
2. Investigate why validation-window F1 varies.
3. Determine whether an appropriate stable reference period exists.
4. Finalize the reference F1 and eligible-window requirements using validation evidence.
5. Define controlled harmless and harmful traffic-shift experiments.
6. Implement and test Strategy A.
7. Implement and test Strategy B.
8. Implement and test Strategy C.
9. Build reproducible software tests.
10. Conduct the complete experimental comparison.

## 15. Important Future Research Questions

- How sensitive are results to the degradation threshold?
- How does minimum labelled sample size affect F1 reliability?
- How should high-cardinality categorical features be monitored?
- How do biased or non-random label delays affect performance monitoring?
- Does combined monitoring provide useful warning lead time?
- Can the strategies generalize beyond the selected UNSW-NB15 capture sessions?
- Which feature groups contribute to performance degradation or false warnings?

These questions must be addressed through evidence and experiments rather than assumptions.

## 16. Data and File Management Rules

- Never modify the original raw dataset files.
- Keep raw datasets outside the Git repository.
- Do not commit large generated model files by default.
- Do not commit large generated prediction files by default.
- Commit reproducible source code, research documentation, tests, and appropriate small result summaries.
- Document how generated results can be reproduced.
- Keep research decisions and unresolved questions documented as the methodology evolves.
