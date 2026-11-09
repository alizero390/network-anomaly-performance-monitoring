# Project TODO

This document tracks implementation, research, testing, and documentation progress.

Status definitions:

- [x] Completed.
- [ ] Pending.
- [~] In progress.

## 1. Dataset and Data Integrity

- [x] Inspect original UNSW-NB15 dataset files.
- [x] Establish the 49-column feature mapping.
- [x] Audit raw dataset chronology.
- [x] Identify January and February capture sessions.
- [x] Establish chronological February training, validation, and test partitions.
- [x] Audit initial feature selection.
- [x] Verify numerical and categorical feature conversions.
- [x] Investigate hexadecimal destination-port values.
- [ ] Create automated dataset integrity tests.
- [ ] Document reproducible dataset preparation.
- [ ] Verify that original raw files remain unchanged.

## 2. Baseline Classifier

- [x] Implement initial Random Forest baseline.
- [x] Fit preprocessing using training data.
- [x] Train baseline classifier.
- [x] Generate validation predictions.
- [x] Calculate overall validation metrics.
- [x] Calculate validation-window metrics.
- [x] Save baseline summary.
- [ ] Add automated baseline tests.
- [x] Audit attack-category composition across validation windows (Generic is 69% of attacks and drives attack-share swings; Fuzzers cause 89% of misses).
- [x] Within-category recall by period (73% of the low/high recall gap is category mix, 27% is Fuzzers recall; Fuzzers recall 0.386 in windows 1-10).
- [ ] Compare features of Fuzzers in windows 1-10 with later Fuzzers traffic.
- [x] Scoping literature search (literature/scoping_review.md).
- [x] Run robustness runs locally (feb_hgb, jan_rf, jan_hgb); see results/robustness_summary.md.
- [ ] Systematic search in Scopus, IEEE Xplore, ACM DL and Google Scholar; log in literature/search_log.md.
- [x] Download and profile improved CIC-IDS-2017 (results/cicids2017_profile).
- [x] Run CIC-IDS-2017 (cic_rf, cic_hgb) and attribute alarms (results/alarm_attribution).
- [x] Re-run CIC-IDS-2017 runs after the timestamp fix (times corrected, metrics identical).
- [ ] Strategy B design: minimum labelled attacks per window, persistence rule for zero recall, reference from pre-deployment labelled data.
- [x] Investigate variation in window-level F1 (see results/attack_share/README.md: 88% of F1 variance is real recall/FPR change, 17% attack share alone).
- [ ] Establish a defensible stable reference period (windows 1-10 are a low-attack, low-performance regime; see results/attack_share/README.md, finding 4).
- [ ] Determine minimum labelled sample requirements.

## 3. Strategy A — Input-Distribution Monitoring

- [ ] Implement numerical feature distribution tests.
- [ ] Implement categorical feature distribution tests.
- [ ] Implement Benjamini-Hochberg correction.
- [ ] Implement combined-feature warning logic.
- [ ] Calibrate warning threshold using validation data.
- [ ] Retain individual-feature monitoring results for ablation.
- [ ] Test stable traffic behaviour.
- [ ] Test harmless distribution shifts.
- [ ] Measure false warnings.
- [ ] Evaluate computational overhead.

## 4. Strategy B — Delayed Performance Monitoring

- [ ] Design prediction and label identifier matching.
- [ ] Implement simulated label delays.
- [ ] Implement partial label availability.
- [ ] Define minimum labelled sample requirements.
- [ ] Implement eligible-window handling.
- [ ] Implement F1 degradation calculation.
- [ ] Implement two-consecutive-window confirmation.
- [ ] Test insufficient-label scenarios.
- [ ] Test delayed and partially available labels.
- [ ] Evaluate detection delay and missed events.
- [ ] Consider ADWIN as a secondary comparison.

## 5. Strategy C — Combined Monitoring

- [ ] Define monitoring state transitions.
- [ ] Implement provisional warnings from Strategy A.
- [ ] Implement performance confirmation from Strategy B.
- [ ] Preserve the independent performance-confirmation path.
- [ ] Define and calibrate the warning association period.
- [ ] Record confirmed and unconfirmed warnings.
- [ ] Calculate warning lead time.
- [ ] Test all state transitions.
- [ ] Compare results with Strategies A and B.

## 6. Controlled Research Experiments

- [ ] Define stable traffic scenario.
- [ ] Define harmless traffic-shift scenario.
- [ ] Define harmful traffic-shift scenario.
- [ ] Establish verified degradation events.
- [ ] Run experiments with no label delay.
- [ ] Run experiments with 5-window label delay.
- [ ] Run experiments with 10-window label delay.
- [ ] Run experiments with 100% label availability.
- [ ] Run experiments with 50% label availability.
- [ ] Run experiments with 20% label availability.
- [ ] Repeat experiments using reproducible seeds.
- [ ] Calculate uncertainty estimates.
- [ ] Compare all three strategies.

## 7. Software Testing

- [x] Establish a pytest test structure.
- [ ] Test dataset integrity.
- [~] Test chronological ordering and partition boundaries (cutoff logic tested; full-data check pending).
- [x] Test preprocessing and feature conversion.
- [ ] Test baseline prediction behaviour.
- [ ] Test F1 degradation rules.
- [ ] Test label-release simulation.
- [ ] Test Strategy A.
- [ ] Test Strategy B.
- [ ] Test Strategy C.
- [ ] Test event matching and repeated-alert counting.
- [ ] Run the complete test suite before final experiments.

## 8. Research Documentation

- [x] Create PROJECT_CONTEXT.md.
- [x] Create RESEARCH_OBJECTIVES.md.
- [x] Create RESEARCH_DECISIONS.md.
- [x] Create README.md.
- [x] Create CHANGELOG.md.
- [x] Document software requirements (pinned requirements.txt).
- [ ] Document experiment configurations.
- [ ] Document dataset preparation and access requirements.
- [~] Maintain literature review notes (literature/ folder created).
- [ ] Document supervisor feedback and responses.
- [ ] Document final experimental results.

## 9. Git and Reproducibility

- [x] Initialize local Git repository.
- [x] Create private GitHub repository.
- [x] Establish main branch.
- [x] Create .gitignore.
- [x] Exclude generated model and prediction files.
- [x] Review files before staging.
- [x] Create initial Git commit.
- [ ] Connect local repository to GitHub.
- [x] Push main branch.
- [ ] Verify remote repository contents.
- [ ] Commit future research and implementation changes regularly.

- [ ] Re-run the baseline in the pinned environment and confirm identical results.

## 10. Final Thesis and Publication Preparation

- [ ] Complete targeted literature review.
- [ ] Establish research gap using supporting literature.
- [ ] Finalize experimental methodology.
- [ ] Complete primary experiments.
- [ ] Complete sensitivity and ablation experiments.
- [ ] Analyze and interpret results.
- [ ] Prepare research tables and figures.
- [ ] Write methodology chapter.
- [ ] Write experimental results chapter.
- [ ] Write discussion and limitations.
- [ ] Prepare final thesis.
- [ ] Prepare conference presentation or research article.

## 11. Immediate Next Actions

1. Audit attack-category composition across validation windows.
2. Investigate the variation in baseline window-level F1.
3. Establish whether a stable reference period can be justified.
4. Define minimum labelled sample requirements.
5. Finalize Strategy A calibration.
6. Begin monitoring implementation only after the relevant design decisions are sufficiently specified.

