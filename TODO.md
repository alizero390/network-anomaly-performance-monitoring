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
- [x] Structured web search for Paper 1 (literature/structured_search.md): novelty assessed per claim.
- [ ] Run the database queries in literature/database_queries.md (Scopus, IEEE Xplore, eLibrary) and export results (Zoghi 2024: read).
- [ ] Add calibrated F1 (Siblini et al.) as a comparison metric in the attack-share simulation.
- [x] Download and profile improved CIC-IDS-2017 (results/cicids2017_profile).
- [x] Run CIC-IDS-2017 (cic_rf, cic_hgb) and attribute alarms (results/alarm_attribution).
- [x] Re-run CIC-IDS-2017 runs after the timestamp fix (times corrected, metrics identical).
- [ ] Strategy B design: minimum labelled attacks per window, persistence rule for zero recall, reference from pre-deployment labelled data.
- [x] Investigate variation in window-level F1 (see results/attack_share/README.md: 88% of F1 variance is real recall/FPR change, 17% attack share alone).
- [ ] Establish a defensible stable reference period (windows 1-10 are a low-attack, low-performance regime; see results/attack_share/README.md, finding 4).
- [ ] Determine minimum labelled sample requirements.

## 3. Strategy A — Input-Distribution Monitoring

- [x] Numerical (Kolmogorov-Smirnov) and categorical (chi-square) tests, Benjamini-Hochberg correction, proportion threshold q (`nadmon.strategies`, D10).
- [x] Calibrate q on stable validation streams; variant A_natural (D16).
- [x] Validation and one-time test run (`results/strategies/`): on test, the fixed validation reference made A warn on 100% of streams before any change.
- [x] D21: moving reference (A_rolling) and B-anchored reference (A_anchored): validation and test runs done (`results/strategy_a_rolling/FINDINGS.md`). On test: 0% false warnings on stable streams (fixed reference: 100%); on real time-ordered windows A still flags every window.
- [x] D22: minimum effect size (A_floor, C_active_floor): validation and test runs done; criteria not met (`results/strategy_a_floor/FINDINGS.md`). RQ1 answered: label-free monitoring cannot replace label-based monitoring on real traffic.
- [ ] Single-feature ablation (D10).
- [ ] Measure computational overhead.

## 4. Strategy B — Delayed Performance Monitoring

- [x] Label delays, partial availability, minimum labelled sample (n_min, m_min) and cohort pooling (D7, D8).
- [x] Calibrated-F1 rule, two consecutive eligible cohorts, re-arm (D5, D9).
- [x] Validation and one-time test run: every harmful stream detected, no false alerts under random labels.
- [x] Alert-first (biased) labels and inverse-probability weighting, B_ipw_eff, B_ipw_ess (D17-D20, Paper 2).
- [x] D23: real test-window alarms attributed: all missed Fuzzers, dip 43-57 mostly attack-mix change (`results/test_alarm_attribution/FINDINGS.md`).
- [x] D23: alarm-drop sensitivity 0.03 / 0.10 on validation and test: 0.05 kept (`results/threshold_sensitivity/FINDINGS.md`).
- [ ] ADWIN as a secondary comparison (optional).

## 5. Strategy C — Combined Monitoring

- [x] C passive and C active, association period L calibrated per delay (D11).
- [x] Validation and test: C active faster than B in 58% of harmful streams on validation, 26% on test (never slower).
- [x] C_active_rolling (D21): faster than B in 54% of harmful test streams, never slower.

## 6. Controlled Research Experiments

- [x] Scenarios S0, H1-H3, X1-X2 plus rare and gradual variants; ground truth by expected calibrated F1 (D3, D4).
- [x] Delays 0/5/10, availability 100/50/20%, alert-first condition; 200 streams each; Wilson intervals and paired tests (D13, D14).
- [x] Real windows in time order (validation and test).
- [ ] Attribute the real test alarms (windows 45-49 and 54) to attack categories.
- [x] D21 runs: validation (calibration), then one test run.
- [ ] Find the cause of the small B differences from the earlier runs (FINDINGS D21, section 4).

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

1. Draft thesis chapters (English, international structure) in Google Docs, starting with chapters 3 and 5.
2. Paper 1: transfer to Computer Networks (started 2026-11-23), then wait for the decision.
3. Attribute the real test alarms (windows 45-49 and 54) to attack categories.
4. Thesis outline, chapter by chapter, from the existing results.
5. Later: API and dashboard on top of the monitoring modules.
