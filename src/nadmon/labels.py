"""Simulated label feedback for Strategy B: availability, delay, cohorts and pooling.

Design spec decisions D7 and D8 (STRATEGY_DESIGN_SPEC.md):

- Each record is labelled or not (availability). Default: independently with
  probability ``p``, regardless of class or prediction. Alternative "alert-first":
  predicted attacks are labelled with ``p_alert`` and predicted normal records with
  ``p_normal``, as when analysts triage alerts first.
- A window's labels are all released at the end of window ``w + delay``.
- Labels stay with the window their records came from (the cohort).
- A cohort is eligible when it has at least ``n_min`` labelled attacks and ``m_min``
  labelled normal records. An ineligible cohort is pooled with the following windows,
  up to ``max_span`` windows; if still short, it is ineligible (never read as stable).

Windows are numbered from 0 here; reports add 1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

AVAILABILITY_MODES = ("random", "alert_first")


def n_min_for_recall(recall: float, drop: float = 0.05, z: float = 2.326) -> int:
    """Labelled attacks needed so sampling noise alone rarely moves recall by ``drop``.

    ``ceil(z^2 * r(1 - r) / drop^2)``; z = 2.326 is a one-sided 1% chance per cohort.
    Returns at least 1.
    """
    if not 0 <= recall <= 1:
        raise ValueError("recall must be in [0, 1]")
    return max(1, math.ceil(z**2 * recall * (1 - recall) / drop**2))


def label_mask(
    n_records: int,
    availability: float,
    seed: int,
    mode: str = "random",
    y_pred: np.ndarray | None = None,
    p_alert: float = 0.9,
    p_normal: float = 0.1,
) -> np.ndarray:
    """Boolean mask: which records ever receive a label.

    ``mode="random"`` uses ``availability`` for every record. ``mode="alert_first"``
    ignores ``availability`` and needs ``y_pred``.
    """
    rng = np.random.default_rng(seed)
    u = rng.random(n_records)
    if mode == "random":
        if not 0 <= availability <= 1:
            raise ValueError("availability must be in [0, 1]")
        return u < availability
    if mode == "alert_first":
        if y_pred is None or len(y_pred) != n_records:
            raise ValueError("alert_first needs y_pred with one value per record")
        p = np.where(np.asarray(y_pred) == 1, p_alert, p_normal)
        return u < p
    raise ValueError(f"mode must be one of {AVAILABILITY_MODES}")


def cohort_counts(
    y_true: np.ndarray, y_pred: np.ndarray, labelled: np.ndarray, window_size: int
) -> pd.DataFrame:
    """Labelled confusion counts per window (complete windows only).

    Columns: window, tp, fp, fn, tn (labelled records only), labelled, records.
    """
    n = len(y_true) // window_size
    cut = n * window_size
    yt = np.asarray(y_true[:cut]).reshape(n, window_size)
    yp = np.asarray(y_pred[:cut]).reshape(n, window_size)
    lab = np.asarray(labelled[:cut], dtype=bool).reshape(n, window_size)
    return pd.DataFrame(
        {
            "window": np.arange(n),
            "tp": ((yt == 1) & (yp == 1) & lab).sum(axis=1),
            "fp": ((yt == 0) & (yp == 1) & lab).sum(axis=1),
            "fn": ((yt == 1) & (yp == 0) & lab).sum(axis=1),
            "tn": ((yt == 0) & (yp == 0) & lab).sum(axis=1),
            "labelled": lab.sum(axis=1),
            "records": window_size,
        }
    )


@dataclass(frozen=True)
class PoolingRule:
    n_min: int
    m_min: int = 500
    max_span: int = 5


def pool_cohorts(counts: pd.DataFrame, rule: PoolingRule, delay: int) -> pd.DataFrame:
    """Group consecutive windows into evaluation cohorts.

    Walks forward from the first window: a cohort grows one window at a time until it
    has ``n_min`` labelled attacks and ``m_min`` labelled normal records, or reaches
    ``max_span`` windows. The next cohort starts after it. A cohort can be evaluated
    once the labels of its last window are released: ``available_at = last + delay``.

    Returns one row per cohort: first, last, span, tp, fp, fn, tn, attacks, normals,
    eligible, available_at.
    """
    if delay < 0:
        raise ValueError("delay must be >= 0")
    tp, fp, fn, tn = (counts[c].to_numpy() for c in ("tp", "fp", "fn", "tn"))
    windows = counts["window"].to_numpy()
    rows = []
    i, n = 0, len(counts)
    while i < n:
        j = i
        while True:
            a = int(tp[i : j + 1].sum() + fn[i : j + 1].sum())
            m = int(fp[i : j + 1].sum() + tn[i : j + 1].sum())
            eligible = a >= rule.n_min and m >= rule.m_min
            if eligible or j - i + 1 >= rule.max_span or j == n - 1:
                break
            j += 1
        rows.append(
            {
                "first": int(windows[i]),
                "last": int(windows[j]),
                "span": j - i + 1,
                "tp": int(tp[i : j + 1].sum()),
                "fp": int(fp[i : j + 1].sum()),
                "fn": int(fn[i : j + 1].sum()),
                "tn": int(tn[i : j + 1].sum()),
                "attacks": a,
                "normals": m,
                "eligible": eligible,
                "available_at": int(windows[j]) + delay,
            }
        )
        i = j + 1
    return pd.DataFrame(rows)


def released_by(cohorts: pd.DataFrame, t: int) -> pd.DataFrame:
    """Cohorts whose labels are available at the end of window ``t``."""
    return cohorts[cohorts["available_at"] <= t]
