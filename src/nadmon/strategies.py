"""Monitoring strategies A, B and C (design spec D5, D6, D9-D12).

Time is counted in windows (0-based). A window's inputs are known at the end of that
window; its labels at the end of window ``w + delay`` (``nadmon.labels``).

- **Strategy A** (input distribution, no labels): per window, each feature is compared
  with a reference sample (Kolmogorov-Smirnov for numeric features, chi-square for
  categorical features), p-values are corrected with Benjamini-Hochberg, and the window
  is flagged when at least a proportion ``q`` of features changed. A warning needs
  ``consecutive`` flagged windows in a row.
- **Strategy B** (performance, delayed labels): each labelled cohort's metric is
  compared with a fixed reference; an alarm needs ``consecutive`` flagged eligible cohorts
  in a row. After an alarm the monitor stays alarmed until ``rearm`` eligible cohorts in
  a row are not flagged (D12).
- **Strategy C**: *passive* raises B's alarms and labels each A warning as confirmed
  (a B alarm within the association period) or unconfirmed; *active* additionally lets
  B confirm on a single flagged cohort while an A warning is active.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from nadmon.attack_share import calibrated_f1

# ----------------------------------------------------------------------------
# Strategy A: input-distribution tests
# ----------------------------------------------------------------------------

MIN_EXPECTED = 5  # chi-square: categories expected less often are merged into "other"


@dataclass
class Reference:
    """Reference sample for Strategy A, prepared once."""

    numeric: Mapping[str, np.ndarray]
    categorical: Mapping[str, pd.Series]

    @classmethod
    def from_frame(
        cls, frame: pd.DataFrame, numeric: Sequence[str], categorical: Sequence[str]
    ) -> Reference:
        return cls(
            numeric={c: np.sort(frame[c].to_numpy(dtype=float)) for c in numeric},
            categorical={c: frame[c].astype(str).value_counts() for c in categorical},
        )

    @property
    def features(self) -> list[str]:
        return list(self.numeric) + list(self.categorical)


def chi_square_p(reference_counts: pd.Series, window_values: pd.Series) -> float:
    """Chi-square test of a window's category counts against the reference counts.

    Categories whose expected count in either sample is below ``MIN_EXPECTED`` are
    merged into one "other" category; categories unseen in the reference count as other.
    Returns 1.0 when fewer than two categories remain.
    """
    win = window_values.astype(str).value_counts()
    cats = reference_counts.index.union(win.index)
    table = np.vstack(
        [reference_counts.reindex(cats, fill_value=0), win.reindex(cats, fill_value=0)]
    ).astype(float)
    totals = table.sum(axis=1, keepdims=True)
    col = table.sum(axis=0)
    expected = totals * col / col.sum()
    small = (expected < MIN_EXPECTED).any(axis=0)
    if small.any():
        table = np.column_stack([table[:, ~small], table[:, small].sum(axis=1)])
        table = table[:, table.sum(axis=0) > 0]
    if table.shape[1] < 2:
        return 1.0
    return float(stats.chi2_contingency(table, correction=False)[1])


def window_feature_pvalues(reference: Reference, window: pd.DataFrame) -> pd.Series:
    """Raw p-value per feature for one window."""
    p = {}
    for c, ref in reference.numeric.items():
        p[c] = float(stats.ks_2samp(ref, window[c].to_numpy(dtype=float), method="asymp").pvalue)
    for c, ref_counts in reference.categorical.items():
        p[c] = chi_square_p(ref_counts, window[c])
    return pd.Series(p)


def changed_features(pvalues: pd.Series, alpha: float = 0.01) -> pd.Series:
    """Benjamini-Hochberg: True for features whose adjusted p-value is at most alpha."""
    adjusted = stats.false_discovery_control(pvalues.to_numpy(), method="bh")
    return pd.Series(adjusted <= alpha, index=pvalues.index)


def changed_proportion(
    reference: Reference, windows: Sequence[pd.DataFrame], alpha: float = 0.01
) -> np.ndarray:
    """Proportion of features changed in each window."""
    return np.array(
        [changed_features(window_feature_pvalues(reference, w), alpha).mean() for w in windows]
    )


def run_warnings(flagged: np.ndarray, consecutive: int = 2) -> list[int]:
    """Windows at which a run of ``consecutive`` flagged windows completes.

    After a warning, a new warning needs a fresh run (the flagged run must break first).
    """
    out, run, active = [], 0, False
    for i, f in enumerate(np.asarray(flagged, dtype=bool)):
        run = run + 1 if f else 0
        if not f:
            active = False
        if run >= consecutive and not active:
            out.append(i)
            active = True
    return out


def a_warnings(proportions: np.ndarray, q: float, consecutive: int = 2) -> list[int]:
    """Strategy A warning windows: proportion of changed features >= q, ``consecutive`` times."""
    return run_warnings(np.asarray(proportions) >= q, consecutive)


def calibrate_q(
    stable_streams: Sequence[np.ndarray],
    target_rate: float = 0.05,
    consecutive: int = 2,
    grid: Sequence[float] | None = None,
) -> float:
    """Smallest q for which at most ``target_rate`` of stable streams raise a warning.

    ``stable_streams`` holds each S0 stream's per-window changed-feature proportions.
    The grid defaults to the proportions observed (plus a value above all of them).
    """
    if grid is None:
        observed = np.unique(np.concatenate([np.asarray(s) for s in stable_streams]))
        grid = list(observed[observed > 0]) + [float(observed.max()) + 1e-9]
    for q in sorted(grid):
        rate = np.mean([len(a_warnings(s, q, consecutive)) > 0 for s in stable_streams])
        if rate <= target_rate:
            return float(q)
    raise ValueError("no q in the grid meets the target rate")


def calibrate_q_windows(proportions: np.ndarray, target_rate: float = 0.05) -> float:
    """Smallest q flagging at most ``target_rate`` of the given (real) windows.

    Used for variant A_natural: the threshold is set on the real time-ordered validation
    windows instead of resampled stable streams.
    """
    props = np.asarray(proportions, dtype=float)
    grid = sorted(set(props[props > 0])) + [float(props.max()) + 1e-9]
    for q in grid:
        if np.mean(props >= q) <= target_rate:
            return float(q)
    raise ValueError("no q meets the target rate")


# ----------------------------------------------------------------------------
# Strategy B: performance on delayed labels
# ----------------------------------------------------------------------------

B_METRICS = ("f1_calibrated", "f1")


def cohort_metric(cohorts: pd.DataFrame, metric: str, reference_share: float) -> np.ndarray:
    """Metric of each labelled cohort; NaN where undefined."""
    tp, fp, fn, tn = (cohorts[c].to_numpy(dtype=float) for c in ("tp", "fp", "fn", "tn"))
    with np.errstate(divide="ignore", invalid="ignore"):
        if metric == "f1":
            denom = 2 * tp + fp + fn
            return np.where(denom > 0, 2 * tp / denom, np.nan)
        if metric == "f1_calibrated":
            recall = np.where(tp + fn > 0, tp / (tp + fn), np.nan)
            fpr = np.where(fp + tn > 0, fp / (fp + tn), np.nan)
            return calibrated_f1(recall, fpr, reference_share)
    raise ValueError(f"metric must be one of {B_METRICS}")


@dataclass(frozen=True)
class BRule:
    reference: float
    metric: str = "f1_calibrated"
    reference_share: float = 0.198
    drop: float = 0.05
    consecutive: int = 2
    rearm: int = 2


def b_monitor(
    cohorts: pd.DataFrame,
    rule: BRule,
    boosted: Sequence[tuple[int, int]] = (),
    boosted_consecutive: int = 1,
) -> pd.DataFrame:
    """Run Strategy B over cohorts in order of label release.

    ``boosted`` lists (start, end) window intervals, inclusive, during which a cohort
    released then needs only ``boosted_consecutive`` flagged cohorts (Strategy C active).
    Returns the cohorts with columns value, eligible_eval, flagged, alarm, in_alarm.
    """
    out = cohorts.sort_values(["available_at", "first"]).reset_index(drop=True).copy()
    out["value"] = cohort_metric(out, rule.metric, rule.reference_share)
    eligible = out["eligible"].to_numpy(dtype=bool) & np.isfinite(out["value"].to_numpy())
    flagged = eligible & (out["value"].to_numpy() <= rule.reference - rule.drop)
    alarm = np.zeros(len(out), dtype=bool)
    in_alarm_col = np.zeros(len(out), dtype=bool)
    released = out["available_at"].to_numpy(dtype=int)
    run = calm = 0
    in_alarm = False
    for i in range(len(out)):
        if not eligible[i]:
            in_alarm_col[i] = in_alarm
            continue
        t = int(released[i])
        need = rule.consecutive
        if any(s <= t <= e for s, e in boosted):
            need = boosted_consecutive
        if flagged[i]:
            run += 1
            calm = 0
            if not in_alarm and run >= need:
                alarm[i] = True
                in_alarm = True
        else:
            run = 0
            if in_alarm:
                calm += 1
                if calm >= rule.rearm:
                    in_alarm = False
                    calm = 0
        in_alarm_col[i] = in_alarm
    out["eligible_eval"] = eligible
    out["flagged"] = flagged
    out["alarm"] = alarm
    out["in_alarm"] = in_alarm_col
    return out


def b_alarm_times(monitored: pd.DataFrame) -> list[int]:
    """Windows (label release times) at which B raised an alarm."""
    return [int(t) for t in monitored.loc[monitored["alarm"], "available_at"]]


# ----------------------------------------------------------------------------
# Strategy C
# ----------------------------------------------------------------------------


def association_period(delay: int, extra: int = 5) -> int:
    """Default association period L = delay + extra windows (D11, before calibration)."""
    return delay + extra


def calibrate_association(gaps: Sequence[int], quantile: float = 0.95) -> int:
    """Smallest L covering ``quantile`` of warning-to-confirmation gaps (in windows)."""
    if len(gaps) == 0:
        raise ValueError("no gaps to calibrate on")
    return int(np.quantile(np.asarray(gaps, dtype=float), quantile, method="inverted_cdf"))


def classify_warnings(
    warnings: Sequence[int], alarms: Sequence[int], period: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Strategy C passive bookkeeping (RESEARCH_DECISIONS.md section 6).

    Returns (warnings table: window, confirmed, confirmed_at, lead_time;
    alarms table: window, preceded_by_warning, warning_at).
    """
    w_rows = []
    for w in warnings:
        hits = [a for a in alarms if w <= a <= w + period]
        w_rows.append(
            {
                "window": w,
                "confirmed": bool(hits),
                "confirmed_at": hits[0] if hits else None,
                "lead_time": hits[0] - w if hits else None,
            }
        )
    a_rows = []
    for a in alarms:
        before = [w for w in warnings if a - period <= w <= a]
        a_rows.append(
            {
                "window": a,
                "preceded_by_warning": bool(before),
                "warning_at": before[-1] if before else None,
            }
        )
    cols_w = ["window", "confirmed", "confirmed_at", "lead_time"]
    cols_a = ["window", "preceded_by_warning", "warning_at"]
    return pd.DataFrame(w_rows, columns=cols_w), pd.DataFrame(a_rows, columns=cols_a)


def c_active(
    cohorts: pd.DataFrame, rule: BRule, warnings: Sequence[int], period: int
) -> pd.DataFrame:
    """Strategy C active: B with single-cohort confirmation during [warning, warning + L]."""
    return b_monitor(cohorts, rule, boosted=[(w, w + period) for w in warnings])
