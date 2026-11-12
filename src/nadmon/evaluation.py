"""Scoring of monitoring events and their statistics (design spec D12, D13).

Each controlled stream has one possible event: the change at the onset window. An alarm
is attributed by the data it was computed from: a B alarm by the last window of the
cohort that confirmed it, an A warning by its window. On a harmful stream, an alarm from
data at or after the onset is a true alert; every other alarm is a false alert. Detection
delay is the time the alarm was raised minus the onset (both in windows), so label delay
is included.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import stats


def score_events(
    alarm_data_windows: Sequence[int],
    alarm_times: Sequence[int],
    onset: int,
    harmful: bool,
) -> dict[str, float | int | bool]:
    """Score one stream for one strategy.

    ``alarm_data_windows[i]`` is the last data window behind alarm i, ``alarm_times[i]``
    the window at which it was raised.
    """
    data = np.asarray(alarm_data_windows, dtype=int)
    times = np.asarray(alarm_times, dtype=int)
    after = data >= onset
    if harmful:
        true_times = times[after]
        n_false = int((~after).sum())
    else:
        true_times = times[:0]
        n_false = len(data)
    detected = bool(len(true_times))
    return {
        "detected": detected,
        "detection_delay": float(true_times.min() - onset) if detected else np.nan,
        "false_alerts": n_false,
        "any_false_alert": n_false > 0,
        "alarms": len(data),
    }


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Proportion with a Wilson score interval: (estimate, low, high)."""
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_median(
    values: Sequence[float], n_boot: int = 2000, seed: int = 0
) -> tuple[float, float, float]:
    """Median with a percentile bootstrap 95% interval; NaN when there are no values."""
    v = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    if len(v) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    meds = np.median(rng.choice(v, size=(n_boot, len(v)), replace=True), axis=1)
    return (float(np.median(v)), float(np.quantile(meds, 0.025)), float(np.quantile(meds, 0.975)))


def summarise(results: pd.DataFrame, by: Sequence[str]) -> pd.DataFrame:
    """Per group: streams, event recall (harmful only), false-alert rate, delays.

    ``results`` needs columns from :func:`score_events` plus ``harmful`` and ``by``.
    """
    rows = []
    for key, g in results.groupby(list(by), sort=True):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key, strict=True))
        n = len(g)
        row["streams"] = n
        fa, fa_lo, fa_hi = wilson(int(g["any_false_alert"].sum()), n)
        row.update(
            false_alert_rate=fa,
            false_alert_low=fa_lo,
            false_alert_high=fa_hi,
            mean_false_alerts=float(g["false_alerts"].mean()),
        )
        if bool(g["harmful"].iloc[0]):
            rec, lo, hi = wilson(int(g["detected"].sum()), n)
            med, mlo, mhi = bootstrap_median(g["detection_delay"])
        else:
            rec = lo = hi = med = mlo = mhi = np.nan
        row.update(
            event_recall=rec,
            event_recall_low=lo,
            event_recall_high=hi,
            median_delay=med,
            median_delay_low=mlo,
            median_delay_high=mhi,
        )
        rows.append(row)
    return pd.DataFrame(rows)


def mcnemar_p(a: Sequence[bool], b: Sequence[bool]) -> float:
    """Exact McNemar test on paired outcomes (two-sided binomial on discordant pairs)."""
    a, b = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool)
    only_a, only_b = int((a & ~b).sum()), int((~a & b).sum())
    if only_a + only_b == 0:
        return 1.0
    return float(stats.binomtest(only_a, only_a + only_b, 0.5).pvalue)


def wilcoxon_p(x: Sequence[float], y: Sequence[float]) -> float:
    """Wilcoxon signed-rank test on pairs where both values are finite; NaN if too few."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    d = x[keep] - y[keep]
    if len(d) < 5 or np.all(d == 0):
        return np.nan
    return float(stats.wilcoxon(x[keep], y[keep], zero_method="wilcox").pvalue)


def paired_comparison(
    results: pd.DataFrame, a: str, b: str, by: Sequence[str] = ("scenario", "condition")
) -> pd.DataFrame:
    """Compare strategy ``a`` with ``b`` on the same streams (D13)."""
    rows = []
    keys = ["stream", *by]
    left = results[results["strategy"] == a].set_index(keys)
    right = results[results["strategy"] == b].set_index(keys)
    joined = left.join(right, lsuffix="_a", rsuffix="_b", how="inner")
    for key, g in joined.groupby(list(by), sort=True):
        key = key if isinstance(key, tuple) else (key,)
        row = {"a": a, "b": b, **dict(zip(by, key, strict=True)), "streams": len(g)}
        row["false_alert_p"] = mcnemar_p(g["any_false_alert_a"], g["any_false_alert_b"])
        if bool(g["harmful_a"].iloc[0]):
            row["detection_p"] = mcnemar_p(g["detected_a"], g["detected_b"])
            row["delay_p"] = wilcoxon_p(g["detection_delay_a"], g["detection_delay_b"])
        else:
            row["detection_p"] = row["delay_p"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)
