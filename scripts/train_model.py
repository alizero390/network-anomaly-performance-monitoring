"""Train a model on one capture session and save its validation predictions.

Usage (from the repository root, virtual environment active):

    python scripts/train_model.py --session feb --model hgb
    python scripts/train_model.py --session jan --model rf
    python scripts/train_model.py --session jan --model hgb

Sessions: feb (February 18, frozen split) or jan (January 22-23, same 50/20/30
chronological rule). Models: rf (the baseline Random Forest) or hgb (histogram
gradient boosting). The test partition is never loaded.

Outputs in results/runs/<session>_<model>/:
    summary.json, validation_window_metrics.csv (committed)
    validation_predictions.csv (not committed; includes attack categories)
Model: models/<session>_<model>.joblib (not committed).

Then run:  python scripts/analyze_attack_share.py --run <session>_<model>
"""

from __future__ import annotations

import argparse
import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd

from nadmon import dataset, sessions
from nadmon.config import load_paths
from nadmon.metrics import binary_metrics, window_metrics
from nadmon.models import MODELS, RANDOM_STATE
from nadmon.provenance import run_metadata

warnings.filterwarnings("ignore", category=FutureWarning)

MIN_ATTACKS = 100  # per partition; fewer makes recall and F1 meaningless


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session", choices=sorted(sessions.SESSIONS), required=True)
    parser.add_argument("--model", choices=sorted(MODELS), required=True)
    args = parser.parse_args()

    session = sessions.SESSIONS[args.session]
    run_name = f"{args.session}_{args.model}"
    paths = load_paths()
    paths.check_raw_files()
    paths.ensure_output_dirs()
    out = paths.results_dir / "runs" / run_name
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n========== {run_name}: SPLIT ==========")
    all_ts, all_labels = sessions.read_timestamps_and_labels(paths.raw_files)
    if len(all_ts) != sessions.DATASET_TOTAL:
        raise RuntimeError(
            f"Total record count {len(all_ts):,} does not match the audited "
            f"{sessions.DATASET_TOTAL:,}."
        )
    counts = sessions.check_sessions_cover_dataset(all_ts)
    print("Records per session:", counts)

    in_session = (all_ts >= session.start) & (all_ts < session.end)
    split = sessions.split_session(all_ts[in_session], session, all_labels[in_session])
    print(
        f"Rule {session.rule} | total {split.total:,} | train {split.train_end:,} | "
        f"validation {split.validation_end - split.train_end:,} | "
        f"after validation (not loaded) {split.total - split.validation_end:,}"
    )

    print(f"\n========== {run_name}: LOAD ==========")
    data = sessions.load_training_and_validation(
        paths.raw_files, session, split, extra_columns=[dataset.ATTACK_CAT_INDEX]
    )
    X, y = dataset.preprocess(data)
    category = dataset.normalize_attack_category(data[dataset.ATTACK_CAT_INDEX]).to_numpy()
    mismatch = int(((y == 0) != (category == "Normal")).sum())
    print("Label/category mismatches:", mismatch)

    X_train, X_val = X.iloc[: split.train_end], X.iloc[split.train_end :]
    y_train, y_val = y[: split.train_end], y[split.train_end :]
    val_ts = data[dataset.STIME_INDEX].to_numpy()[split.train_end :]
    print("Training attack %:", round(float(y_train.mean() * 100), 2))
    print("Validation attack %:", round(float(y_val.mean() * 100), 2))
    for part, labels in (("training", y_train), ("validation", y_val)):
        if labels.sum() < MIN_ATTACKS:
            raise RuntimeError(
                f"The {part} partition has {int(labels.sum())} attacks (minimum "
                f"{MIN_ATTACKS}); detection performance cannot be measured with this split."
            )

    print(f"\n========== {run_name}: TRAIN ==========")
    pipeline = MODELS[args.model]()
    start = time.time()
    pipeline.fit(X_train, y_train)
    training_seconds = time.time() - start
    print("Training seconds:", round(training_seconds, 1))
    joblib.dump(pipeline, paths.models_dir / f"{run_name}.joblib")

    start = time.time()
    # predict() matches the baseline exactly (ties at 0.5 go to the normal class).
    predictions = pipeline.predict(X_val)
    probabilities = pipeline.predict_proba(X_val)[:, 1]
    prediction_seconds = time.time() - start

    overall = binary_metrics(y_val, predictions)
    for key, value in overall.items():
        print(f"{key}: {round(value, 6) if isinstance(value, float) else value}")

    windows = window_metrics(y_val, predictions, val_ts, dataset.WINDOW_SIZE)
    windows.to_csv(out / "validation_window_metrics.csv", index=False, lineterminator="\n")

    pd.DataFrame(
        {
            "SortedIndex": np.arange(split.train_end, split.validation_end),
            "Timestamp": val_ts,
            "TrueLabel": y_val,
            "Prediction": predictions,
            "AttackProbability": probabilities,
            "AttackCategory": category[split.train_end :],
        }
    ).to_csv(out / "validation_predictions.csv", index=False, lineterminator="\n")

    summary = {
        "run": run_name,
        "session": args.session,
        "model": args.model,
        "split": {
            "rule": session.rule,
            "total": split.total,
            "train_end": split.train_end,
            "validation_end": split.validation_end,
            "cutoff_timestamp": split.cutoff,
        },
        "records_per_session": counts,
        "label_category_mismatches": mismatch,
        "training_attack_share": float(y_train.mean()),
        "validation_attack_share": float(y_val.mean()),
        "random_state": RANDOM_STATE,
        "threshold": 0.5,
        "classifier": repr(pipeline.named_steps["classifier"]),
        **{k: v for k, v in overall.items()},
        "training_seconds": float(training_seconds),
        "prediction_seconds": float(prediction_seconds),
        "provenance": run_metadata(),
    }
    with open(out / "summary.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=4)

    print(f"\nSaved to {out}")
    print(f"Next: python scripts/analyze_attack_share.py --run {run_name}")


if __name__ == "__main__":
    main()
