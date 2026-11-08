# Network Anomaly Detection Performance Monitoring

Research project investigating the detection of genuine performance degradation in network anomaly detection systems under changing traffic conditions and delayed ground-truth feedback.

## Research Overview

Network traffic distributions change over time. However, a change in traffic does not necessarily mean that an anomaly detection model has become less effective.

This project investigates how to distinguish harmless traffic changes from changes that genuinely reduce detection performance.

Three monitoring strategies are compared:

- **Strategy A — Input-Distribution Monitoring:** Detects changes in network traffic without requiring ground-truth labels.
- **Strategy B — Delayed Performance-Based Monitoring:** Detects performance degradation using ground-truth labels as they become available.
- **Strategy C — Combined Monitoring:** Uses input-distribution warnings and delayed performance confirmation.

The research also investigates how delayed and partially available labels affect monitoring reliability.

## Main Research Question

How do input-distribution monitoring, delayed performance-based monitoring, and combined monitoring compare in detecting genuine network anomaly-detection performance degradation under controlled traffic changes and delayed or partially available ground-truth labels?

## Dataset

The initial experimental dataset is **UNSW-NB15**.

The original dataset contains four CSV files with 2,540,047 records in total.

The February 18, 2015 capture session is used for the initial chronological baseline experiment.

### Dataset Partition

| Partition | Records |
|---|---:|
| Training | 726,426 |
| Validation | 290,575 |
| Testing | 435,843 |
| Total | 1,452,844 |

The original dataset is not included in this repository. Obtain it from its official source and set its location in `configs/paths.toml` (see Setup below).

**Important:** The original raw dataset must remain unchanged.

## Baseline Model

The initial baseline is a Random Forest classifier.

### Model Configuration

- Algorithm: Random Forest.
- Number of trees: 200.
- Class weights: Balanced.
- Random seed: 42.
- Classification threshold: 0.5.
- Numerical features: 23.
- Categorical features: 3.
- Total input features: 26.

### Validation Results

| Metric | Value |
|---|---:|
| Accuracy | 0.98929 |
| Precision | 0.977826 |
| Recall | 0.967868 |
| F1-score | 0.972821 |
| False Positive Rate | 0.00542 |

These results represent the initial validation baseline, not final test performance.

The model has not yet been evaluated through the complete monitoring framework.

## Setup (Windows, cmd)

Requires Python 3.11 or newer (tested on 3.13 and 3.14). From the repository folder:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
copy configs\paths.example.toml configs\paths.toml
```

Edit `configs\paths.toml` so `data_dir` points to the folder containing `UNSW-NB15_1.csv` to `UNSW-NB15_4.csv`. Then check the environment and run the tests:

```bat
python scripts\check_environment.py
pytest
```

Re-run the baseline with `python scripts\baseline.py`. The generated model and predictions are written to `models\` and `results\` and are not committed.

The exact package versions are pinned in `requirements.txt`. scikit-learn is pinned to 1.8.0 because the saved baseline model was trained with that version.

## Repository Structure

```text
network-anomaly-performance-monitoring/
├── src/nadmon/                  # Reusable research code
│   ├── config.py                # Machine-specific paths (configs/paths.toml)
│   ├── dataset.py               # Column layout, February split, preprocessing
│   ├── metrics.py               # Overall and window-level metrics
│   ├── attack_share.py          # Attack-share effects, decomposition, resampling
│   ├── sessions.py              # January and February sessions and their splits
│   ├── models.py                # Random Forest and gradient boosting pipelines
│   └── provenance.py            # Git commit and package versions for each run
├── scripts/
│   ├── baseline.py              # Train and validate the Random Forest baseline
│   ├── analyze_attack_share.py  # Window performance vs attack share (results/attack_share)
│   ├── export_validation_categories.py  # Export attack_cat for validation rows (run locally)
│   ├── train_model.py           # Train rf/hgb on the feb or jan session
│   ├── compare_runs.py          # Side-by-side table of all analysed runs
│   └── run_robustness.bat       # Runs feb_hgb, jan_rf, jan_hgb and the comparison (Windows)
│   ├── check_environment.py     # Check versions, dataset path and model loading
├── tests/                       # pytest suite
├── configs/
│   └── paths.example.toml       # Copy to paths.toml (not committed)
├── results/
│   ├── baseline_summary.json
│   ├── validation_window_metrics.csv
│   ├── attack_share/            # Findings, tables and figures (baseline)
│   ├── runs/                    # Robustness runs: <session>_<model>/
│   └── comparison.md            # All runs side by side
├── literature/                  # Scoping review, search log, references.bib
├── models/                      # Generated models; not committed
├── requirements.txt             # Pinned runtime packages
├── requirements-dev.txt         # Adds pytest and ruff
└── pyproject.toml               # Package, pytest and ruff configuration
```

## Project Documentation

| File | Description |
|---|---|
| PROJECT_CONTEXT.md | Overall research background, dataset, baseline, and progress |
| RESEARCH_OBJECTIVES.md | Research aim, questions, objectives, and scope |
| RESEARCH_DECISIONS.md | Approved methodology, decisions, and unresolved questions |
| TODO.md | Implementation and research task tracker |
| CHANGELOG.md | Record of significant project changes |
| literature/README.md | How literature notes and references are organised |
