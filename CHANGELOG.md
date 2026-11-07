# Changelog

All significant project changes are recorded here in reverse chronological order.

The format follows these categories:

- Added: New functionality or documentation.
- Changed: Changes to existing functionality or methodology.
- Fixed: Bug fixes.
- Removed: Removed functionality or files.
- Research: Research findings and methodological updates.

## [Unreleased]

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
