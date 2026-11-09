"""How window-level metrics depend on the share of attacks in a window.

Two separate effects can make a metric fall in a window:

1. Arithmetic: with recall (TPR) and false positive rate (FPR) held fixed,
   precision, F1 and MCC still change when the attack share changes.
2. Performance: the model really detects better or worse in that window
   (TPR or FPR changes), for example because the traffic mix is different.

``decompose_f1`` separates the two on observed windows; ``resample_at_shares``
isolates effect 1 by holding per-class performance fixed and varying only the
attack share.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

# Metrics where a lower value means worse detection.
HIGHER_IS_BETTER = ("f1", "mcc", "balanced_accuracy", "recall")


# ----------------------------------------------------------------------------
# Closed-form metrics from rates
# ----------------------------------------------------------------------------


def f1_from_rates(tpr, fpr, share):
    """F1 implied by TPR, FPR and attack share (all scalars or arrays)."""
    tpr, fpr, share = np.asarray(tpr), np.asarray(fpr), np.asarray(share)
    tp = tpr * share
    fn = (1 - tpr) * share
    fp = fpr * (1 - share)
    denom = 2 * tp + fp + fn
    return np.divide(2 * tp, denom, out=np.zeros_like(denom, dtype=float), where=denom > 0)


def mcc_from_rates(tpr, fpr, share):
    """Matthews correlation implied by TPR, FPR and attack share."""
    tpr, fpr, share = np.asarray(tpr), np.asarray(fpr), np.asarray(share)
    flagged = tpr * share + fpr * (1 - share)  # fraction predicted as attack
    denom = np.sqrt(flagged * (1 - flagged))
    numer = (tpr - fpr) * np.sqrt(share * (1 - share))
    return np.divide(numer, denom, out=np.zeros_like(denom, dtype=float), where=denom > 0)


# ----------------------------------------------------------------------------
# Confusion-count metrics (vectorised over many windows)
# ----------------------------------------------------------------------------


def metrics_from_counts(tp, fp, fn, tn) -> dict[str, np.ndarray]:
    """Window metrics from confusion counts.

    A metric that is undefined for a window (for example recall in a window with no
    attacks) is NaN, not 0, so monitoring treats the window as ineligible for that
    metric instead of as a performance drop. F1 is 0 when a window has no attacks but
    some false positives (2TP + FP + FN > 0), and NaN only when it is 0/0.
    """
    tp, fp, fn, tn = (np.asarray(v, dtype=float) for v in (tp, fp, fn, tn))

    def ratio(a, b):
        return np.divide(a, b, out=np.full_like(a, np.nan), where=b > 0)

    recall = ratio(tp, tp + fn)
    fpr = ratio(fp, fp + tn)
    precision = ratio(tp, tp + fp)
    f1 = ratio(2 * tp, 2 * tp + fp + fn)
    mcc_den = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ratio(tp * tn - fp * fn, mcc_den)
    return {
        "attack_share": np.nan_to_num(ratio(tp + fn, tp + fp + fn + tn)),
        "recall": recall,
        "fpr": fpr,
        "precision": precision,
        "f1": f1,
        "mcc": mcc,
        "balanced_accuracy": (recall + (1 - fpr)) / 2,
    }


def window_table(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scores: np.ndarray,
    timestamps: np.ndarray,
    window_size: int,
) -> pd.DataFrame:
    """Threshold and ranking metrics for consecutive complete windows."""
    n_windows = len(y_true) // window_size
    cut = n_windows * window_size
    yt = y_true[:cut].reshape(n_windows, window_size)
    yp = y_pred[:cut].reshape(n_windows, window_size)

    tp = ((yt == 1) & (yp == 1)).sum(axis=1)
    fp = ((yt == 0) & (yp == 1)).sum(axis=1)
    fn = ((yt == 1) & (yp == 0)).sum(axis=1)
    tn = ((yt == 0) & (yp == 0)).sum(axis=1)

    table = pd.DataFrame(metrics_from_counts(tp, fp, fn, tn))
    table.insert(0, "window", np.arange(1, n_windows + 1))
    sc = scores[:cut].reshape(n_windows, window_size)
    both_classes = [0 < yt[i].sum() < window_size for i in range(n_windows)]
    table["roc_auc"] = [
        roc_auc_score(yt[i], sc[i]) if both_classes[i] else np.nan for i in range(n_windows)
    ]
    table["average_precision"] = [
        average_precision_score(yt[i], sc[i]) if both_classes[i] else np.nan
        for i in range(n_windows)
    ]
    table[["tp", "fp", "fn", "tn"]] = np.column_stack([tp, fp, fn, tn])
    table["start_utc"] = pd.to_datetime(timestamps[:cut:window_size], unit="s", utc=True)
    return table


# ----------------------------------------------------------------------------
# Decomposition of observed window F1
# ----------------------------------------------------------------------------


def r_squared(observed: np.ndarray, predicted: np.ndarray) -> float:
    """R² of predicted against observed, over pairs where both are defined."""
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    keep = np.isfinite(observed) & np.isfinite(predicted)
    observed, predicted = observed[keep], predicted[keep]
    if len(observed) < 2:
        return float("nan")
    total = ((observed - observed.mean()) ** 2).sum()
    return float(1 - ((observed - predicted) ** 2).sum() / total) if total > 0 else float("nan")


def decompose_f1(windows: pd.DataFrame, tpr: float, fpr: float, share: float) -> pd.DataFrame:
    """Add two counterfactual F1 columns to a window table.

    ``f1_share_only``: the window's attack share with the pooled TPR/FPR, i.e.
    what F1 would be if only the attack share changed.
    ``f1_performance_only``: the window's own TPR/FPR at the pooled attack
    share, i.e. what F1 would be if only detection performance changed.
    """
    out = windows.copy()
    out["f1_share_only"] = f1_from_rates(tpr, fpr, out["attack_share"])
    out["f1_performance_only"] = f1_from_rates(out["recall"], out["fpr"], share)
    return out


# ----------------------------------------------------------------------------
# Controlled resampling: vary attack share, hold per-class performance fixed
# ----------------------------------------------------------------------------


def resample_at_shares(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    shares: Sequence[float],
    window_size: int,
    n_windows: int,
    seed: int,
) -> pd.DataFrame:
    """Simulate windows with a fixed attack share by sampling with replacement.

    Attacks and normal records are drawn separately from the pooled validation
    predictions, so the model's per-class behaviour is identical at every
    share; only the mix changes. Returns one row per simulated window.
    """
    rng = np.random.default_rng(seed)
    attack_hit = y_pred[y_true == 1] == 1  # true positive per attack record
    normal_hit = y_pred[y_true == 0] == 1  # false positive per normal record

    frames = []
    for share in shares:
        n_attacks = int(round(share * window_size))
        n_normals = window_size - n_attacks
        att_idx = rng.integers(0, len(attack_hit), size=(n_windows, n_attacks))
        nor_idx = rng.integers(0, len(normal_hit), size=(n_windows, n_normals))
        tp = attack_hit[att_idx].sum(axis=1)
        fp = normal_hit[nor_idx].sum(axis=1)
        metrics = metrics_from_counts(tp, fp, n_attacks - tp, n_normals - fp)
        frame = pd.DataFrame(metrics)
        frame.insert(0, "target_share", share)
        frame.insert(1, "replicate", np.arange(n_windows))
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def alarm_rate(
    values: np.ndarray,
    reference: float,
    drop: float,
    consecutive: int,
    stream_length: int,
) -> float:
    """Fraction of simulated monitoring streams that raise a degradation alarm.

    Windows are grouped into streams of ``stream_length``. A stream alarms if
    the metric is at least ``drop`` below ``reference`` in ``consecutive``
    windows in a row (the protocol's Strategy B rule).
    """
    values = np.asarray(values)
    n_streams = len(values) // stream_length
    flagged = (values[: n_streams * stream_length] <= reference - drop).reshape(
        n_streams, stream_length
    )
    run = np.zeros(n_streams, dtype=int)
    alarmed = np.zeros(n_streams, dtype=bool)
    for step in range(stream_length):
        run = np.where(flagged[:, step], run + 1, 0)
        alarmed |= run >= consecutive
    return float(alarmed.mean())
