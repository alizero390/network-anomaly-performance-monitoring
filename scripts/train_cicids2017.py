"""Train on improved CIC-IDS-2017 and predict the later days.

Usage (repository root, virtual environment active):

    python scripts/train_cicids2017.py --model rf                # Paper 1 split
    python scripts/train_cicids2017.py --model hgb
    python scripts/train_cicids2017.py --model rf --split cic2   # thesis split (D2)
    python scripts/train_cicids2017.py --model hgb --split cic2

Split ``cic`` (Paper 1): train Monday-Thursday, predict Friday. Outputs in
results/runs/cic_<model>/ (same layout as train_model.py, so
scripts/analyze_attack_share.py --run cic_<model> works on them):
    summary.json, validation_window_metrics.csv (committed)
    validation_predictions.csv (not committed)

Split ``cic2`` (D2): train Monday-Wednesday plus the first 50% of Thursday, validate on
the last 50% of Thursday, monitor Friday. Outputs in results/runs/cic2_<model>/:
    summary.json, validation_window_metrics.csv, monitor_window_metrics.csv (committed)
    validation_predictions.csv, monitor_predictions.csv (not committed)

Model: models/<run>.joblib (not committed).
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
    parser.add_argument("--split", choices=["cic", "cic2"], default="cic")
    args = parser.parse_args()
    if args.split == "cic2":
        run_cic2(args.model)
        return

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


def predictions_frame(
    part: pd.DataFrame, y, predictions, probabilities, start: int
) -> pd.DataFrame:
    """Per-record output; port and protocol are kept for the scenario strata (not committed)."""
    return pd.DataFrame(
        {
            "SortedIndex": np.arange(start, start + len(part)),
            "Timestamp": part["timestamp"].to_numpy(),
            "TrueLabel": y,
            "Prediction": predictions,
            "AttackProbability": probabilities,
            "AttackCategory": part["category"].to_numpy(),
            "DstPort": part["Dst Port"].to_numpy(),
            "Protocol": part["Protocol"].to_numpy(),
        }
    )


def recall_by_category(part: pd.DataFrame, predictions) -> pd.DataFrame:
    return (
        part.assign(detected=np.asarray(predictions) == 1)
        .loc[lambda d: d["label"] == 1]
        .groupby("category")["detected"]
        .agg(["size", "mean"])
        .rename(columns={"size": "flows", "mean": "recall"})
    )


def run_cic2(model: str) -> None:
    """Thesis split D2: Monday-Wednesday + first half of Thursday | rest of Thursday | Friday."""
    run_name = f"cic2_{model}"
    folder = load_cicids2017_dir()
    out = RESULTS / "runs" / run_name
    out.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n========== {run_name}: LOAD ==========")
    data, report = cic.load_days(folder, cic.TRAIN_DAYS)
    monitor, monitor_report = cic.load_days(folder, (cic.MONITOR_DAY,))
    cut = cic.split_day_boundary(data)
    train, valid = data.iloc[:cut], data.iloc[cut:]
    X, y = cic.preprocess(data)
    X_train, X_val, y_train, y_val = X.iloc[:cut], X.iloc[cut:], y[:cut], y[cut:]
    X_mon, y_mon = cic.preprocess(monitor)
    categorical, numeric = cic.feature_columns(data.columns)
    print(f"Thursday boundary: {valid['time'].iloc[0]} (row {cut:,})")
    for name, part, labels in (
        ("Training", train, y_train),
        ("Validation", valid, y_val),
        ("Friday", monitor, y_mon),
    ):
        cats = part.loc[part["label"] == 1, "category"].value_counts().to_dict()
        print(f"{name:<10} flows {len(labels):>9,} | attacks {labels.mean():.2%} | {cats}")
    for name, labels in (("training", y_train), ("validation", y_val)):
        if labels.sum() < cic.MIN_ATTACKS:
            raise RuntimeError(
                f"The {name} partition has {int(labels.sum())} attacks (minimum "
                f"{cic.MIN_ATTACKS}); the D2 split cannot be used as planned."
            )

    print(f"\n========== {run_name}: TRAIN ==========")
    pipeline = MODELS[model](categorical, numeric)
    start = time.time()
    pipeline.fit(X_train, y_train)
    training_seconds = time.time() - start
    print("Training seconds:", round(training_seconds, 1))
    joblib.dump(pipeline, MODELS_DIR / f"{run_name}.joblib")

    results = {}
    for name, part, X_part, y_part, first in (
        ("validation", valid, X_val, y_val, cut),
        ("monitor", monitor, X_mon, y_mon, 0),
    ):
        predictions = pipeline.predict(X_part)
        probabilities = pipeline.predict_proba(X_part)[:, 1]
        overall = binary_metrics(y_part, predictions)
        per_category = recall_by_category(part, predictions)
        print(f"\n{name.capitalize()} ({'Thursday, second half' if first else 'Friday'}):")
        for key in ("recall", "false_positive_rate", "precision", "f1"):
            print(f"  {key}: {overall[key]:.4f}")
        print(per_category.to_string())
        windows = window_metrics(y_part, predictions, part["timestamp"].to_numpy(), WINDOW_SIZE)
        windows.to_csv(out / f"{name}_window_metrics.csv", index=False, lineterminator="\n")
        predictions_frame(part, y_part, predictions, probabilities, first).to_csv(
            out / f"{name}_predictions.csv", index=False, lineterminator="\n"
        )
        results[name] = {
            **overall,
            "records": int(len(y_part)),
            "attack_share": float(y_part.mean()),
            "first_time": str(part["time"].iloc[0]),
            "last_time": str(part["time"].iloc[-1]),
            "recall_by_category": per_category.reset_index().to_dict(orient="records"),
        }

    summary = {
        "run": run_name,
        "dataset": "CIC-IDS-2017 (improved; Engelen et al. 2021, Liu et al. 2022)",
        "split": {
            "rule": "D2: mon-wed + first 50% of thursday | last 50% of thursday | friday",
            "train_end": cut,
            "validation_end": int(len(data)),
            "boundary_time": str(valid["time"].iloc[0]),
            "split_share": cic.SPLIT_SHARE,
        },
        "cleaning": {"train_and_validation": report, "monitor": monitor_report},
        "features": {"categorical": categorical, "numeric": numeric},
        "training_attack_share": float(y_train.mean()),
        "training_categories": train.loc[train["label"] == 1, "category"].value_counts().to_dict(),
        "validation": results["validation"],
        "monitor": results["monitor"],
        "random_state": RANDOM_STATE,
        "threshold": 0.5,
        "classifier": repr(pipeline.named_steps["classifier"]),
        "training_seconds": float(training_seconds),
        "provenance": run_metadata(),
    }
    with open(out / "summary.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=4, default=str)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
