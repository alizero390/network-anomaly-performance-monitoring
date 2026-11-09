"""Train on improved CIC-IDS-2017 Monday-Thursday and predict Friday.

Usage (repository root, virtual environment active):

    python scripts/train_cicids2017.py --model rf
    python scripts/train_cicids2017.py --model hgb

Outputs in results/runs/cic_<model>/ (same layout as train_model.py, so
scripts/analyze_attack_share.py --run cic_<model> works on them):
    summary.json, validation_window_metrics.csv (committed)
    validation_predictions.csv (not committed)
Model: models/cic_<model>.joblib (not committed).
"""

from __future__ import annotations

import argparse
import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd

from nadmon import cicids2017 as cic
from nadmon.config import PROJECT_DIR, load_cicids2017_dir
from nadmon.dataset import WINDOW_SIZE
from nadmon.metrics import binary_metrics, window_metrics
from nadmon.models import MODELS, RANDOM_STATE
from nadmon.provenance import run_metadata

warnings.filterwarnings("ignore", category=FutureWarning)

RESULTS = PROJECT_DIR / "results"
MODELS_DIR = PROJECT_DIR / "models"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=sorted(MODELS), required=True)
    args = parser.parse_args()

    run_name = f"cic_{args.model}"
    folder = load_cicids2017_dir()
    out = RESULTS / "runs" / run_name
    out.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n========== {run_name}: LOAD ==========")
    train, train_report = cic.load_days(folder, cic.TRAIN_DAYS)
    monitor, monitor_report = cic.load_days(folder, (cic.MONITOR_DAY,))
    X_train, y_train = cic.preprocess(train)
    X_val, y_val = cic.preprocess(monitor)
    categorical, numeric = cic.feature_columns(train.columns)
    print(f"Training flows {len(X_train):,} ({y_train.mean():.2%} attacks)")
    print(f"Friday flows   {len(X_val):,} ({y_val.mean():.2%} attacks)")
    print(f"Features: {len(categorical)} categorical, {len(numeric)} numeric")

    print(f"\n========== {run_name}: TRAIN ==========")
    pipeline = MODELS[args.model](categorical, numeric)
    start = time.time()
    pipeline.fit(X_train, y_train)
    training_seconds = time.time() - start
    print("Training seconds:", round(training_seconds, 1))
    joblib.dump(pipeline, MODELS_DIR / f"{run_name}.joblib")

    start = time.time()
    predictions = pipeline.predict(X_val)
    probabilities = pipeline.predict_proba(X_val)[:, 1]
    prediction_seconds = time.time() - start

    overall = binary_metrics(y_val, predictions)
    for key, value in overall.items():
        print(f"{key}: {round(value, 6) if isinstance(value, float) else value}")

    timestamps = monitor["timestamp"].to_numpy()
    windows = window_metrics(y_val, predictions, timestamps, WINDOW_SIZE)
    windows.to_csv(out / "validation_window_metrics.csv", index=False, lineterminator="\n")

    pd.DataFrame(
        {
            "SortedIndex": np.arange(len(monitor)),
            "Timestamp": timestamps,
            "TrueLabel": y_val,
            "Prediction": predictions,
            "AttackProbability": probabilities,
            "AttackCategory": monitor["category"].to_numpy(),
        }
    ).to_csv(out / "validation_predictions.csv", index=False, lineterminator="\n")

    per_category = (
        monitor.assign(detected=predictions == 1)
        .loc[lambda d: d["label"] == 1]
        .groupby("category")["detected"]
        .agg(["size", "mean"])
        .rename(columns={"size": "flows", "mean": "recall"})
    )
    print("\nFriday recall per attack category:")
    print(per_category.to_string())

    summary = {
        "run": run_name,
        "dataset": "CIC-IDS-2017 (improved; Engelen et al. 2021, Liu et al. 2022)",
        "split": {
            "rule": "train_mon_thu_monitor_fri",
            "train_days": list(cic.TRAIN_DAYS),
            "monitor_day": cic.MONITOR_DAY,
            "train_end": int(len(X_train)),
            "validation_end": int(len(X_train) + len(X_val)),
        },
        "cleaning": {"train": train_report, "monitor": monitor_report},
        "features": {"categorical": categorical, "numeric": numeric},
        "training_attack_share": float(y_train.mean()),
        "validation_attack_share": float(y_val.mean()),
        "training_categories": train.loc[train["label"] == 1, "category"].value_counts().to_dict(),
        "validation_records": int(len(X_val)),
        "recall_by_category": per_category.reset_index().to_dict(orient="records"),
        "random_state": RANDOM_STATE,
        "threshold": 0.5,
        "classifier": repr(pipeline.named_steps["classifier"]),
        **overall,
        "training_seconds": float(training_seconds),
        "prediction_seconds": float(prediction_seconds),
        "provenance": run_metadata(),
    }
    with open(out / "summary.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=4, default=str)

    print(f"\nSaved to {out}")
    print(f"Next: python scripts/analyze_attack_share.py --run {run_name}")


if __name__ == "__main__":
    main()
