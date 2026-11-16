"""Label-bias study on a natural stream: CIC-IDS-2017 Friday in time order (D20).

Fixed before any run (approved 2026-11-16). On CIC-IDS-2017 the detectors raise
(almost) no false positives and the validation half of Thursday holds one attack type,
so the resampled scenarios of the UNSW-NB15 study cannot be built. Instead, Friday is
monitored in its real time order, and its real events are the harmful periods.

- **Reference** (per detector): recall, n_min and calibrated F1 from its predictions on
  the validation half of Thursday; the reference share pi0 is that half's attack share.
  Window size, drop, consecutive, re-arm, m_min, max_span and the label delay (5) are the
  frozen UNSW-NB15 values.
- **Ground truth per window:** calibrated F1 with all labels. A window is *defined* when
  it holds at least n_min attacks, and *harmful* when defined and its calibrated F1 is at
  least 0.10 below the reference (the scenario rule of the UNSW-NB15 study).
- **Events:** maximal runs of harmful windows; undefined windows inside a run do not
  break it, a defined window that is not harmful does.
- **Alarms** are judged on their cohort (the windows ``first..last`` it pooled), with all
  labels: *true* if the cohort's calibrated F1 is at least 0.10 below the reference,
  *false* if less than 0.05 below it (the alarm threshold), *borderline* otherwise
  (reported, not counted as false).
- An event is **detected** when a true alarm's cohort overlaps its windows; the delay is
  the alarm's release time minus the event's first window.
- **Label draws:** the 32 conditions of the UNSW-NB15 study, each with 200 independent
  label masks (seeds).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from nadmon import experiment as ex
from nadmon import labels as lb
from nadmon import strategies as st

HARM = 0.10  # harmful drop of calibrated F1, as in nadmon.scenarios
STRATEGIES = ("B_F1", "B", "B_ipw", "B_ipw_eff", "B_ipw_ess")


@dataclass(frozen=True)
class Truth:
    calibrated: np.ndarray  # calibrated F1 per window with all labels (NaN if undefined)
    defined: np.ndarray
    harmful: np.ndarray
    events: list[tuple[int, int]]  # inclusive window ranges


def _calibrated(tp, fp, fn, tn, pi0) -> np.ndarray:
    frame = pd.DataFrame({"tp": tp, "fp": fp, "fn": fn, "tn": tn})
    return st.cohort_metric(frame, "f1_calibrated", pi0)


def window_truth(y, p, window_size: int, cal: ex.Calibration) -> Truth:
    """Calibrated F1 of every full window with all labels, and the harmful events."""
    counts = lb.cohort_counts(y, p, np.ones(len(y), dtype=bool), window_size)
    values = _calibrated(counts.tp, counts.fp, counts.fn, counts.tn, cal.pi0)
    defined = (counts.tp + counts.fn).to_numpy() >= cal.n_min
    values = np.where(defined, values, np.nan)
    harmful = defined & (values <= cal.reference_f1_calibrated - HARM)
    events, start, last = [], None, None
    for w in range(len(values)):
        if harmful[w]:
            if start is None:
                start = w
            last = w
        elif defined[w] and start is not None:
            events.append((start, last))
            start = None
    if start is not None:
        events.append((start, last))
    return Truth(values, defined, harmful, events)


def judge_alarms(alarms: pd.DataFrame, counts: pd.DataFrame, cal: ex.Calibration) -> pd.Series:
    """'true', 'false' or 'borderline' for each alarm cohort, from all labels."""
    out = []
    for first, last in zip(alarms["first"], alarms["last"], strict=True):
        part = counts.iloc[int(first) : int(last) + 1]
        value = _calibrated(
            [part.tp.sum()], [part.fp.sum()], [part.fn.sum()], [part.tn.sum()], cal.pi0
        )[0]
        gap = cal.reference_f1_calibrated - value
        out.append("true" if gap >= HARM else ("false" if not gap >= 0.05 else "borderline"))
    return pd.Series(out, index=alarms.index, dtype=object)


def score(alarms: pd.DataFrame, verdicts: pd.Series, truth: Truth) -> dict:
    """Events detected, delays and false alarms of one labelled run."""
    true = alarms[verdicts == "true"]
    delays = []
    for start, end in truth.events:
        hit = true[(true["first"] <= end) & (true["last"] >= start)]
        delays.append(float(hit["available_at"].min() - start) if len(hit) else np.nan)
    detected = np.isfinite(delays)
    return {
        "events": len(truth.events),
        "events_detected": int(detected.sum()),
        "median_delay": float(np.nanmedian(delays)) if detected.any() else np.nan,
        "alarms": len(alarms),
        "false_alarms": int((verdicts == "false").sum()),
        "borderline_alarms": int((verdicts == "borderline").sum()),
    }


def run_condition(
    y, p, cond: ex.Condition, cal: ex.Calibration, s: ex.Settings, truth: Truth, seed: int
) -> list[dict]:
    """All strategies for one label draw of one condition."""
    idx = np.arange((len(y) // s.window_size) * s.window_size)
    part = ex.Partition(np.asarray(y), np.asarray(p), np.zeros(len(y)))
    counts = ex._window_counts(part, idx, cond, s, seed)
    full = lb.cohort_counts(part.y[idx], part.p[idx], np.ones(len(idx), dtype=bool), s.window_size)
    cohorts = ex._pool(counts, cond, cal, s)
    pa, pn = ex._assumed_probabilities(cond)
    ess = lb.pool_cohorts(
        counts, lb.PoolingRule(cal.n_min, s.m_min, s.max_span), cond.delay, weights=(1 / pa, 1 / pn)
    )
    variants = {
        "B_F1": (cohorts, "f1"),
        "B": (cohorts, "f1_calibrated"),
        "B_ipw": (ex._ipw(cohorts, cond), "f1_calibrated"),
        "B_ipw_eff": (ex._pool(ex._ipw(counts, cond), cond, cal, s), "f1_calibrated"),
        "B_ipw_ess": (ex._ipw(ess, cond), "f1_calibrated"),
    }
    rows = []
    for name, (data, metric) in variants.items():
        monitored = st.b_monitor(data, ex._b_rule(cal, s, metric))
        alarms = monitored.loc[monitored["alarm"], ["first", "last", "available_at"]]
        verdicts = judge_alarms(alarms, full, cal)
        rows.append({"condition": cond.name, "strategy": name, **score(alarms, verdicts, truth)})
    return rows


def policy_table(results: pd.DataFrame) -> pd.DataFrame:
    """Per condition and strategy: detection share, false-alarm runs, delay."""
    g = results.groupby(["condition", "strategy"], sort=False)
    out = g.agg(
        draws=("events", "size"),
        events=("events", "first"),
        detection_rate=("events_detected", "sum"),
        any_false_alarm=("false_alarms", lambda v: float((v > 0).mean())),
        mean_false_alarms=("false_alarms", "mean"),
        mean_borderline=("borderline_alarms", "mean"),
        median_delay=("median_delay", "median"),
    ).reset_index()
    total = out["draws"] * out["events"]
    out["detection_rate"] = np.where(
        total > 0, out["detection_rate"] / total.where(total > 0, 1), np.nan
    )
    return out
