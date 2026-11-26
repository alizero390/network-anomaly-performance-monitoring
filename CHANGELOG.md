# Changelog

All significant project changes are recorded here in reverse chronological order.

The format follows these categories:

- Added: New functionality or documentation.
- Changed: Changes to existing functionality or methodology.
- Fixed: Bug fixes.
- Removed: Removed functionality or files.
- Research: Research findings and methodological updates.

## [Unreleased]

### Added
- D23 (approved 2026-11-26): attribution of the real test-window alarms (`nadmon.window_attribution`, `scripts/attribute_test_alarms.py`) and the B alarm-threshold sensitivity analysis with drops 0.03 and 0.10 (`scripts/run_threshold_sensitivity.py`); `tests/test_window_attribution.py`.

### Research
- D22 validation and test runs (Ali, 2026-11-26); `results/strategy_a_floor/FINDINGS.md`. No epsilon kept real validation windows at 5% flagged (0.3: 27%); at epsilon 0.3, 21% of real test windows flagged and no harmful change detected: pre-registered criteria not met. On real test windows, an input shift at windows 43-49 preceded B's alarms and moved C_active_floor's alarms about 5 windows earlier (one event).

### Added
- D22 (approved 2026-11-23): Strategy A with a minimum effect size. `strategies.window_feature_tests` (p-value and effect size: Kolmogorov-Smirnov statistic, total variation distance), `nadmon.effect_floor` (A_floor, C_active_floor; epsilon calibrated on real validation windows, q on stable streams), `scripts/run_strategy_a_floor.py` and `tests/test_effect_floor.py`.

### Research
- D21 validation and test runs (Ali, 2026-11-23); `results/strategy_a_rolling/FINDINGS.md`. Both success criteria met on test: A_rolling 0% false warnings on stable streams (fixed reference 100%), C_active_rolling faster than B in 54% of harmful streams (fixed-reference C_active 26%), never slower. On real time-ordered windows A (fixed or rolling) still flags every window: statistical tests detect differences too small to matter (practical-significance floor needed).

### Added
- D21 (approved 2026-11-23): Strategy A with a moving reference. `nadmon.rolling_a` (A_rolling, A_anchored, C_active_rolling; calibration, grid and time-ordered runs on the streams and label draws of the earlier strategy runs), `scripts/run_strategy_a_rolling.py` (validation calibration to `configs/strategy_a_rolling.toml`, then a one-time test run with the same guards as `scripts/run_strategy_test.py`), and `tests/test_rolling_a.py`.

### Added
- `LICENSE` (MIT) and `CITATION.cff`, before making the repository public for the Paper 1 submission.

### Added
- `scripts/plot_label_bias.py`: Paper 2 Figures 2 (false alarms and detection over p_alert x p_normal, per rule) and 3 (against p_normal at p_alert 0.9, 95% Wilson intervals, audit bound 2.5%) for feb_rf and feb_hgb, validation and test, in `results/label_bias/figures/` (PNG, PDF and the plotted values as CSV).

### Research
- CIC-IDS-2017 Friday label-bias runs (Ali, 2026-11-16); section 6 of `results/label_bias/FINDINGS.md`. cic2_rf has two harmful events (missed Portscan variant, DDoS); alert-first labels leave the attack-heavy cohorts without enough labelled normal records, so B, B_ipw and B_ipw_ess go silent while B_ipw_eff detects both events at every policy; no false alarms with correct weights. cic2_hgb has no harmful event; with a halved assumed rate only B_ipw_ess stays free of false alarms.

### Added
- `scripts/run_label_bias_cic.py` and `nadmon.natural_bias` (D20): label-bias study on CIC-IDS-2017 Friday in time order with real events as ground truth; outputs in `results/label_bias/cic2_<model>/`.

### Added
- `scripts/train_cicids2017.py --split cic2` (D2): train Monday-Wednesday plus the first 50% of Thursday, validate on the last 50% of Thursday, monitor Friday (`nadmon.cicids2017.split_day_boundary`). Outputs in `results/runs/cic2_<model>/`; prediction files keep destination port and protocol for the scenario strata. The Paper 1 split is unchanged.

### Research
- Label-bias study for feb_hgb on validation and test (Ali, 2026-11-16); section 5 of `results/label_bias/FINDINGS.md`. The messages for feb_rf hold for feb_hgb (B_ipw_ess 0% false alarms everywhere); only X2 is harmful for feb_hgb on validation and no harmful scenario exists on test.

### Added
- `scripts/run_label_bias.py --model feb_hgb` (D19): the label-bias study for the second detector. Its reference values come from its validation predictions (`nadmon.label_bias.model_reference`) and are written to `configs/reference_feb_hgb.toml`; outputs in `results/label_bias/feb_hgb/<partition>/`, now including `scenarios.csv`.

### Research
- Label-bias study re-run on validation and confirmed on test (Ali, 2026-11-15); `results/label_bias/FINDINGS.md` replaces the validation-only file. B_ipw_ess (Kish effective sample size) keeps false alarms at 0-1% under every policy and under wrongly assumed rates, and stays silent below ~2.5% labelling of normal traffic, matching the bound m_min / (normals per window x max_span).

### Added
- Variant B_ipw_ess (RESEARCH_DECISIONS.md D18): eligibility on the Kish effective sample size of the weighted labels (`labels.kish_ess`, `pool_cohorts(..., weights=...)`). 2 new tests (117 total).

### Fixed
- `pool_cohorts` cast weighted (float) counts to integers, truncating at most one count per cohort for B_ipw_eff. The validation label-bias run must be repeated before the test run.

### Research
- Label-bias study on validation (Ali, 9.2 min) summarised in `results/label_bias/validation/FINDINGS.md`: uncorrected monitoring fails once normal traffic is labelled at 10% or less; B_ipw repairs it down to 5% with 0-1.5% false alerts; at 1-2% the eligibility rule decides the outcome (B_ipw_eff recovers detection, adds false alarms); underestimating the labelling rate of normal traffic is the costly error.

### Added
- Label-bias study for Paper 2 (RESEARCH_DECISIONS.md D17): `nadmon.label_bias` (fixed policy grid with audit sampling and wrong weights) and `scripts/run_label_bias.py` (`--partition validation|test`, no calibration). Label conditions now carry true and assumed labelling probabilities; new variant B_ipw_eff pools and checks eligibility on weighted counts. 1 new test (115 total).

### Research
- One-time test run (Ali, 2026-11-15) summarised in `results/strategies/test/FINDINGS.md`: B with calibrated F1 and B_ipw hold out of sample (B_ipw: false alerts 0-0.5%, detection 99.5-100% under alert-first labels; B: 93.5-100% false alerts); Strategy A warns on every test stream before any change; C-active's speed-up shrinks from 58% to 26% of streams.

### Added
- `scripts/run_strategy_test.py`: the one-time February test run (design spec D1). Reads the frozen `configs/strategies.toml` and recalibrates nothing; refuses to run if the config comes from a quick run, differs from the validation run's `calibration.json`, is uncommitted (checked with git, or confirmed with `--confirm-committed` when git is not on PATH), or a test run already exists (`--resume-identical` only for an interrupted run with a byte-identical config). `--check-only` runs the guards alone.
- `dataset.load_test` (February records after the validation cutoff, count-checked against 435,843); `nadmon.february` (validation/test partitions shared by both scripts); `nadmon.frozen` (config reading, checks, hash).
- 5 tests for the guards (114 in total).

### Research
- Second full validation run (Ali, 2026-11-14) in `results/strategies/validation/FINDINGS.md` sections 7-8: B_ipw removes the alert-first bias (false alerts 100% -> 0%, harmful detection 6-13% -> 100%); A_natural's threshold becomes q = 1.0, so A is either always warning or never warning on real traffic. `configs/strategies.toml` is final for the test run.

### Added
- Variant **B_ipw** (`nadmon.labels.ipw_cohorts`): Strategy B on inverse-probability-weighted counts; removes the alert-first bias on synthetic data (RESEARCH_DECISIONS.md D15).
- Variant **A_natural** and **C_active_natural** (`nadmon.strategies.calibrate_q_windows`): Strategy A's threshold set on the real time-ordered validation windows (D16).
- `configs/strategies.toml` gains `q_natural` and the IPW probabilities; the full validation run must be repeated to fill them before the test run. 4 new tests (109 total).

### Research
- Full validation run (Ali, 200 streams, 127 min) summarised in `results/strategies/validation/FINDINGS.md`: B with calibrated F1 detects every harmful stream with no false alerts under random labels; label delay sets detection delay (delay + 1 window) and scarce labels add up to 6 windows when attacks are rare; A is fastest but warns on all harmless streams and flags 100% of real time-ordered windows; C-active is one window faster than B; alert-first labelling makes B false-alarm on every stable stream and miss most harmful changes.

### Added
- Harder scenario variants `_rare` and `_gradual` for each harmful scenario (`nadmon.scenarios.harder_variants`), and `nadmon.experiment.run_natural` for the real validation windows in time order; both in `run_strategy_experiment.py` (approved 2026-11-12).

### Research
- Quick validation run (Ali, 20 streams): all six scenarios usable; q = 0.038 (one feature in 26); B with calibrated F1 detected every harmful stream with no false alerts, plain F1 alarmed on every H1 stream, A warned on every input shift, C-active one window faster. Near-ceiling results motivated the harder variants.

### Added
- `nadmon.evaluation`: event scoring per stream (D12), Wilson intervals, bootstrap median delay, McNemar and Wilcoxon paired comparisons (D13).
- `nadmon.experiment`: partitions, label conditions, per-stream runs of A, B-F1, B, C-passive and C-active, calibration of Strategy A's q and Strategy C's association period, full grid (D14).
- `scripts/run_strategy_experiment.py`: loads February validation features, calibrates, writes `configs/strategies.toml`, runs the validation grid, writes `results/strategies/validation/`. `--quick` for a short first run.
- 8 end-to-end tests on a synthetic partition (103 tests in total).

### Research
- Synthetic end-to-end check: B detects harmful shifts; A warns on every input shift including harmless ones; plain F1 alarms on fewer attacks while calibrated F1 does not. Alert-first labelling inflates the estimated FPR and makes calibrated F1 alarm on a healthy model (design spec D7 note).

### Changed
- **Decision change (RESEARCH_DECISIONS.md sections 3 and 16):** Strategy B's primary metric is calibrated F1 instead of F1; plain F1 stays as variant B-F1. Approved by Ali on 2026-11-12 with all design-spec decisions D1-D14.

### Added
- `nadmon.strategies`: Strategy A (KS and chi-square tests with sparse categories merged, Benjamini-Hochberg, changed-feature proportion, warnings, calibration of q), Strategy B (cohort metric, alarm rule with alarm state and re-arm, label release times), Strategy C (passive warning classification, active single-cohort confirmation, association period). 14 tests.

### Research
- With benign strata by service, protocol and state, all six scenarios have clean ground truth on February validation; X2 reaches FPR 6.4% via `none|udp|INT` (FPR 24.8%) and `none|udp|REQ`. This strata level is now the standard (design spec D3).
- Scenario check on February validation (Ali's run, 2026-11-12): S0, H1, H2, H3 and X1 have clean ground truth; X2 cannot be built from services alone, because the noisiest benign service has FPR 1.1% (ftp) and moving all benign traffic there lowers calibrated F1 by only about 0.01.

### Changed
- Benign strata can be finer (service, protocol and connection state) to look for concentrated false positives for X2; `export_validation_categories.py` exports Proto and State, and `check_scenarios.py` reports both levels.

### Added
- `nadmon.labels`: label availability (random and alert-first), release delay, labelled cohort counts, cohort pooling and `n_min` (design spec D7, D8).
- `nadmon.scenarios`: strata, compositions, expected calibrated F1, ground-truth classification (D4) and the stream builder with onset and ramp; standard scenarios S0, H1-H3, X1-X2 (D3).
- `scripts/check_scenarios.py`: which scenarios can be built from February validation, plus label-cohort pooling per availability. Writes `results/scenarios/`.
- 17 tests (`tests/test_labels.py`, `tests/test_scenarios.py`).

### Changed
- `scripts/export_validation_categories.py` also exports each record's `Service` (benign strata for H2 and X2). Re-run it before `check_scenarios.py`.

### Added
- `STRATEGY_DESIGN_SPEC.md`: proposed design for Strategies A, B and C under delayed and partial labels (decisions D1-D14, answering the open questions in RESEARCH_DECISIONS.md section 12). Awaiting approval; RESEARCH_DECISIONS.md stays authoritative until then.

### Added
- Calibrated F1 (Siblini et al.) as a monitored metric: `nadmon.attack_share.calibrated_f1`, column `f1_calibrated` in window tables and the resampling simulation, with the run's pooled validation attack share as the reference share. Included in alarm attribution and `results/comparison.md`. Three new tests.

### Changed
- Figure 3 (resampled metrics) uses a legend instead of line-end labels, which overlapped.

### Research
- Calibrated F1 across all six runs (`results/robustness_summary.md`): removes every attack-share and attack-free-window alarm (feb_hgb 9 -> 3, cic_hgb 34 -> 13 alarms), keeps both January false-positive bursts, and has 0-0.5% simulated false alarms at 1% attacks except cic_rf (FPR 0, identical to F1; residual alarms are small-sample recall noise). Added as claim 6 in `paper1_status_and_claims.xlsx`.
- February RF baseline: calibrated F1 gives 0-0.5% simulated false alarms at every attack share (F1 and MCC: 100% at 0.5-2%) and the same real alarms as recall (4 all-window, 1 first-10), all from missed Fuzzers. Existing metrics and alarm counts unchanged.

### Research
- Structured literature search for Paper 1 (`literature/structured_search.md`, 12 new logged queries, 12 new studies including 3 in Russian). No study found combining windowed monitoring of NIDS models, changing attack prevalence and alarm-level evaluation. Prevalence dependence of F1/MCC is known (Guesné et al. 2024; Siblini et al.), so Paper 1 is framed as an empirical study of monitoring-metric behaviour and should add calibrated F1 as a comparison.

### Added
- `scripts/attribute_alarms.py`: labels every confirmed alarm window by cause (missed attacks with category and whether it was seen in training, false-positive burst, too few attacks to judge, attack-share effect), checked against each run's alarm table. Results in `results/alarm_attribution/`.
- `results/cicids2017_findings.xlsx`: spreadsheet of the CIC-IDS-2017 findings.
- CIC-IDS-2017 section and alarm attribution in `results/robustness_summary.md`.

### Fixed
- CIC-IDS-2017 epoch seconds were computed from microseconds as if nanoseconds, so window start times showed 1970. Window order and metrics were unaffected. Re-run the two CIC runs to correct the committed times.

### Added
- CIC-IDS-2017 pipeline: `nadmon.cicids2017` (loading, cleaning, time sorting, features) and `scripts/train_cicids2017.py` (train Monday-Thursday, monitor Friday), analysable with `analyze_attack_share.py --run cic_<model>`. Decisions in RESEARCH_DECISIONS.md, section 14.
- End-to-end CIC-IDS-2017 tests on synthetic day files built on the real header.

### Changed
- Window metrics that are undefined (e.g. recall in a window without attacks) are NaN instead of 0, and the Strategy B rule skips such windows. UNSW-NB15 results are unchanged (verified). Alarm tables gain an `eligible_windows` column.
- Model pipelines accept any feature columns; analysis no longer assumes UNSW-NB15's Generic and Fuzzers categories exist.

### Research
- Four-run robustness summary (`results/robustness_summary.md`). Replicates in all runs: Fuzzers cause 89-98% of missed attacks; under pure attack-share change F1/MCC alarm falsely while recall and balanced accuracy do not. Reference-period sensitivity is February-specific. January shows false positive bursts (windows 12-14) that F1 flags but balanced accuracy hides, so Strategy B should monitor recall and FPR separately.

### Added
- `scripts/profile_cicids2017.py`: profiles the improved CIC-IDS-2017 day files (rows, time ranges, ordering, labels, `Attempted Category`, invalid values) before the experiment is designed. Folder set by `cicids2017_dir` in `configs/paths.toml`.
- Reference for the improved CIC-IDS-2017 / CSE-CIC-IDS-2018 datasets (Liu et al., IEEE CNS 2022).

### Added
- `nadmon.sessions`: January and February capture sessions with the same chronological 50/20/30 split rule (February keeps its frozen counts).
- `nadmon.models`: Random Forest (baseline) and histogram gradient boosting pipelines.
- `scripts/train_model.py`, `scripts/compare_runs.py`, `scripts/run_robustness.bat` for robustness runs on a second model and the January session.
- `analyze_attack_share.py --run <name>` analyses any run; category data come from the run's predictions file.
- End-to-end tests on synthetic raw files for both models.
- Scoping literature review (`literature/scoping_review.md`), search log and 13 new references.
- Robustness-run decisions in RESEARCH_DECISIONS.md, section 13.

### Fixed
- Port conversion extended for the January session: hexadecimal `sport` values are converted like `dsport`, and `-` (no port, 9 January records) is encoded as -1. Preprocessing errors now list failing columns and values. February is unaffected.
- Dataset total in `nadmon.sessions` corrected to the audited 2,540,047 records (was 2,540,044 from the dataset's published description); a test now ties it to PROJECT_CONTEXT.md.

### Research
- January's default validation partition contains no attacks (training: 4.09%). January becomes a replication-only session; its split will be chosen from its full attack timeline (`scripts/describe_session.py`). `train_model.py` now stops when a partition has fewer than 100 attacks.
- January timeline: all 22,215 attacks fall in a two-hour burst (11:49-13:49 UTC, windows 1-38 of 218). January now uses the approved `attack_period_50_50` rule: the attack period is split 50/50 into training and validation; later attack-free traffic is not used.
- `feb_hgb` (gradient boosting, February): recall 0.991, FPR 1.75%, F1 0.961; the reference-period effect and the pure attack-share false alarms replicate.
- Scoping review: Generic dominance (about 65% of UNSW-NB15 attacks) and Fuzzers overlapping normal traffic are already reported at the dataset level (Zoghi and Serpen; Flood et al.). The candidate contribution is their temporal consequence for window-level monitoring and degradation alarms.

### Added
- `nadmon.attack_share`: closed-form F1/MCC from rates, vectorised window metrics (recall, FPR, MCC, balanced accuracy, ROC AUC, average precision), F1 decomposition, controlled attack-share resampling and the Strategy B alarm rule.
- `scripts/analyze_attack_share.py` and results in `results/attack_share/` (tables, figures, README with findings).
- `scripts/export_validation_categories.py` to export validation attack categories on the machine holding the raw data.

### Changed
- Provenance `git_uncommitted_changes` now ignores generated files in `results/`, so it reports only uncommitted code or documentation changes.

### Research
- Window F1 variation is mostly real detection change, not attack-share arithmetic: pooled recall/FPR at each window's attack share explains R² = 0.17 of window F1; each window's own recall/FPR explains R² = 0.88.
- Low-attack windows (two contiguous periods at the start and end of validation) have lower recall (0.868 vs 0.978) and higher FPR (0.79% vs 0.37%).
- Under pure attack-share change, the F1-drop rule raises false alarms in all simulated streams at shares of 2% or less; balanced accuracy and recall do not.
- The candidate reference period (windows 1-10) is itself a low-performance regime; the reference choice changes which windows count as degraded.
- Category audit: Generic attacks are 69% of validation attacks (recall 1.000) and cause the attack-share swings; Fuzzers (recall 0.581) cause 89% of misses. The category mix explains R² = 0.67 of window recall. Recall excluding Generic is 0.895.
- Within-category analysis: of the 0.121 pooled recall gap between low- and high-attack windows, 0.088 (73%) comes from the category mix and 0.032 (27%) from lower recall within categories, all of it Fuzzers (recall 0.386 in windows 1-10, 0.644 in windows 11-49).
- Category analysis split into a local export step and a summary step that runs from the committed category tables; added figures 5 and 6.

### Fixed
- Run provenance now records the git commit even when the git command line is not installed (for example with GitHub Desktop only), by reading it from the `.git` folder.
- Baseline outputs are written with LF line endings on every OS, so re-runs on Windows no longer show unchanged result files as modified.

### Research
- Baseline re-run in the pinned environment (Python 3.14.3, scikit-learn 1.8.0, Windows 11) reproduced all validation metrics exactly.

## 2026-11-07 — Reproducible repository setup

### Added
- Python package `nadmon` under `src/` holding the dataset, metrics, configuration and provenance code previously inside `scripts/baseline.py`.
- Pinned environment (`requirements.txt`, `requirements-dev.txt`, `pyproject.toml`). scikit-learn is pinned to 1.8.0, the version used to train the saved baseline model.
- Machine-specific dataset path in `configs/paths.toml` (template: `configs/paths.example.toml`) or the `NADMON_DATA_DIR` environment variable.
- `scripts/check_environment.py` to confirm package versions, dataset location and model loading.
- pytest suite, including a test that recomputes the validation window metrics from the saved predictions.
- Run provenance (git commit, package versions, platform) recorded in `baseline_summary.json` on the next baseline run.
- Shared VS Code settings with Ruff formatting; `.gitattributes` for consistent line endings.
- `literature/` folder for review notes and references.

### Changed
- `scripts/baseline.py` now uses the `nadmon` package and the configured paths. The training procedure, features, split and model settings are unchanged.
- `.gitignore` now commits shared VS Code settings and ignores the local path configuration.

### Fixed
- Removed byte-order marks from the documentation files.
- Repaired the repository structure section of README.md and updated stale TODO items.


## 2026-11-05 — Initial baseline and documentation

### Added
- Initial project documentation.
- Research context and project background.
- Research aims, questions, and objectives.
- Methodological decision record.
- Project task and progress tracker.
- Git ignore rules for generated models, predictions, datasets, temporary files, and secrets.

### Research
- Established the initial UNSW-NB15 chronological experimental dataset split.
- Completed initial feature-selection and data-conversion audits.
- Trained and evaluated the initial Random Forest baseline.
- Generated validation predictions and window-level metrics.
- Established the initial comparison framework for Strategies A, B, and C.

### Current Baseline
- Random Forest with 200 trees.
- Validation F1-score: 0.972821.
- Validation precision: 0.977826.
- Validation recall: 0.967868.
- Validation false positive rate: 0.00542.

### Pending
- Validation-window attack-category composition audit.
- Investigation of window-level F1 variation.
- Justification of the stable reference period.
- Minimum labelled sample-size determination.
- Implementation of monitoring Strategies A, B, and C.
- Automated software tests.
