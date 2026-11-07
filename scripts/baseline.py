"""Train and validate the Random Forest baseline on the February UNSW-NB15 split.

Usage (from the repository root, with the virtual environment active):

    python scripts/baseline.py

Outputs:
    models/random_forest_baseline.joblib    (not committed)
    results/validation_predictions.csv      (not committed)
    results/validation_window_metrics.csv
    results/baseline_summary.json
"""

from __future__ import annotations

import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from nadmon import dataset
from nadmon.config import load_paths
from nadmon.metrics import binary_metrics, window_metrics
from nadmon.provenance import run_metadata

warnings.filterwarnings("ignore", category=FutureWarning)

N_TREES = 200
RANDOM_STATE = 42
THRESHOLD = 0.5  # RandomForest.predict uses 0.5; recorded for the summary.


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                [dataset.model_column(i) for i in dataset.CATEGORICAL_FEATURES],
            ),
            (
                "numerical",
                "passthrough",
                [dataset.model_column(i) for i in dataset.NUMERIC_FEATURES],
            ),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=N_TREES,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


def main() -> None:
    paths = load_paths()
    paths.check_raw_files()
    paths.ensure_output_dirs()

    print("\n========== STEP 1: FIND CHRONOLOGICAL CUTOFF ==========")
    timestamps = dataset.read_february_timestamps(paths.raw_files)
    print("February timestamps:", len(timestamps))
    cutoff = dataset.find_validation_cutoff(timestamps)
    print("Validation cutoff timestamp:", cutoff)

    print("\n========== STEP 2: LOAD MODEL DATA ==========")
    data = dataset.load_train_validation(paths.raw_files, cutoff)
    print("Records loaded:", len(data))

    print("\n========== STEP 3: PREPROCESS FEATURES ==========")
    X, y = dataset.preprocess(data)
    X_train, X_val = X.iloc[: dataset.TRAIN_END], X.iloc[dataset.TRAIN_END :]
    y_train, y_val = y[: dataset.TRAIN_END], y[dataset.TRAIN_END :]
    val_timestamps = data[dataset.STIME_INDEX].to_numpy()[dataset.TRAIN_END :]

    print("Training records:", len(X_train))
    print("Validation records:", len(X_val))
    print("Features:", len(dataset.FEATURE_INDICES))
    print("Training attack percentage:", round(float(y_train.mean() * 100), 2))
    print("Validation attack percentage:", round(float(y_val.mean() * 100), 2))

    print("\n========== STEP 4-5: BUILD AND TRAIN ==========")
    pipeline = build_pipeline()
    start = time.time()
    pipeline.fit(X_train, y_train)
    training_seconds = time.time() - start
    print("Training time (seconds):", round(training_seconds, 2))

    model_path = paths.models_dir / "random_forest_baseline.joblib"
    joblib.dump(pipeline, model_path)
    print("Model saved:", model_path)

    print("\n========== STEP 6: VALIDATION PREDICTIONS ==========")
    # Timing covers predict and predict_proba together.
    start = time.time()
    predictions = pipeline.predict(X_val)
    probabilities = pipeline.predict_proba(X_val)[:, 1]
    prediction_seconds = time.time() - start
    print("Prediction time (seconds):", round(prediction_seconds, 2))

    print("\n========== STEP 7: OVERALL VALIDATION METRICS ==========")
    overall = binary_metrics(y_val, predictions)
    for key, value in overall.items():
        print(f"{key}: {round(value, 6) if isinstance(value, float) else value}")

    # Outputs use "\n" line endings on every OS so Git sees no spurious changes.
    print("\n========== STEP 8: WINDOW METRICS ==========")
    windows = window_metrics(y_val, predictions, val_timestamps, dataset.WINDOW_SIZE)
    window_path = paths.results_dir / "validation_window_metrics.csv"
    windows.to_csv(window_path, index=False, lineterminator="\n")
    print(windows.to_string(index=False))
    print("\nIncomplete validation tail records:", len(y_val) % dataset.WINDOW_SIZE)

    print("\n========== STEP 9: SAVE VALIDATION PREDICTIONS ==========")
    prediction_path = paths.results_dir / "validation_predictions.csv"
    pd.DataFrame(
        {
            "FebruarySortedIndex": np.arange(dataset.TRAIN_END, dataset.VALIDATION_END),
            "Timestamp": val_timestamps,
            "TrueLabel": y_val,
            "Prediction": predictions,
            "AttackProbability": probabilities,
        }
    ).to_csv(prediction_path, index=False, lineterminator="\n")

    summary = {
        "experiment": "Random Forest baseline",
        "dataset": "UNSW-NB15 February 18 session",
        "training_records": int(len(X_train)),
        "validation_records": int(len(X_val)),
        "features": len(dataset.FEATURE_INDICES),
        "numeric_features": len(dataset.NUMERIC_FEATURES),
        "categorical_features": len(dataset.CATEGORICAL_FEATURES),
        "trees": N_TREES,
        "class_weight": "balanced",
        "random_state": RANDOM_STATE,
        "prediction_threshold": THRESHOLD,
        "accuracy": overall["accuracy"],
        "precision": overall["precision"],
        "recall": overall["recall"],
        "f1": overall["f1"],
        "false_positive_rate": overall["false_positive_rate"],
        "training_seconds": float(training_seconds),
        "prediction_seconds": float(prediction_seconds),
        "provenance": run_metadata(),
    }
    summary_path = paths.results_dir / "baseline_summary.json"
    with open(summary_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=4)

    print("\n========== EXPERIMENT COMPLETE ==========")
    for label, path in [
        ("Model", model_path),
        ("Predictions", prediction_path),
        ("Window metrics", window_path),
        ("Summary", summary_path),
    ]:
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
