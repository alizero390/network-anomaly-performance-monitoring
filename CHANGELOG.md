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
