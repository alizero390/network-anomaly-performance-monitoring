"""Overall and window-level classification metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def confusion_counts(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    """Return (tn, fp, fn, tp) with attack = 1 as the positive class."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return int(tn), int(fp), int(fn), int(tp)


def false_positive_rate(fp: int, tn: int) -> float:
    return fp / (fp + tn) if (fp + tn) else 0.0


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | int]:
    tn, fp, fn, tp = confusion_counts(y_true, y_pred)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": float(false_positive_rate(fp, tn)),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }


def window_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    timestamps: np.ndarray,
    window_size: int,
) -> pd.DataFrame:
    """Metrics for consecutive complete windows of ``window_size`` records.

    Records past the last complete window are not included.
    """
    rows = []
    for window in range(len(y_true) // window_size):
        start = window * window_size
        end = start + window_size
        true_w = y_true[start:end]
        pred_w = y_pred[start:end]
        tn, fp, fn, tp = confusion_counts(true_w, pred_w)
        rows.append(
            {
                "Window": window + 1,
                "Records": window_size,
                "AttackPercent": round(float(true_w.mean() * 100), 2),
                "Precision": precision_score(true_w, pred_w, zero_division=0),
                "Recall": recall_score(true_w, pred_w, zero_division=0),
                "F1": f1_score(true_w, pred_w, zero_division=0),
                "FPR": false_positive_rate(fp, tn),
                "TN": tn,
                "FP": fp,
                "FN": fn,
                "TP": tp,
                "StartUTC": str(pd.to_datetime(timestamps[start], unit="s", utc=True)),
                "EndUTC": str(pd.to_datetime(timestamps[end - 1], unit="s", utc=True)),
            }
        )
    return pd.DataFrame(rows)
