"""Strategy A with a moving reference (decision D21).

On the one-time test run, Strategy A with its fixed validation reference warned on every
stream before any change: one period later the traffic already differed from the
reference. D21 replaces the fixed reference by a recent one.

- **A_rolling** (no labels): window ``w`` is compared with the records of the
  ``lookback`` windows ``w - gap - lookback + 1 .. w - gap`` (by default windows
  ``w-14 .. w-5``). Windows without a full reference are not judged (proportion 0).
- **A_anchored** (ablation, uses labels): the reference is the ``lookback`` most recent
  windows that Strategy B has judged healthy by the end of window ``w``: windows of an
  eligible cohort whose calibrated F1 was not flagged and whose labels were released at
  ``available_at <= w``. Until ``lookback`` such windows exist, windows are not judged.
- **C_active_rolling**: Strategy C active with A_rolling's warnings.

Everything else is Strategy A as frozen (D10): Kolmogorov-Smirnov / chi-square,
Benjamini-Hochberg at ``alpha``, a reference sample of ``a_reference_size`` records,
threshold ``q`` calibrated on validation stable streams (at most 5% with a warning), and
``a_consecutive`` flagged windows for a warning. Streams and label draws are generated
exactly as in :func:`nadmon.experiment.run_grid`, so B's results are reproduced and the
new variants are paired with them.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from nadmon import evaluation as ev
from nadmon import experiment as ex
from nadmon import scenarios as sc
from nadmon import strategies as st

LOOKBACK = 10
GAP = 5
ANCHORED_CONDITIONS = ("d5_p100", "d5_p20")  # A_anchored is run under these only (D21)
ANCHORED_CALIBRATION = "d5_p100"  # q_anchored is calibrated under this condition
STRATEGIES = ("A_rolling", "A_anchored", "B", "C_active_rolling")


@dataclass
class RollingCalibration:
    lookback: int = LOOKBACK
    gap: int = GAP
    q_rolling: float | None = None
    q_anchored: float | None = None
    periods: dict[int, int] = field(default_factory=dict)
    association_gaps: dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ----------------------------------------------------------------------------
# Changed-feature proportions with a moving reference
# ----------------------------------------------------------------------------


def window_frames(part: ex.Partition, idx: np.ndarray, window_size: int) -> list[pd.DataFrame]:
    n = len(idx) // window_size
    return [part.features.iloc[idx[w * window_size : (w + 1) * window_size]] for w in range(n)]


def reference_from_windows(
    frames: Sequence[pd.DataFrame],
    windows: Sequence[int],
    part: ex.Partition,
    size: int,
    rng: np.random.Generator,
) -> st.Reference:
    """Reference sample of at most ``size`` records drawn from the given windows."""
    pool = pd.concat([frames[w] for w in windows], ignore_index=True)
    if len(pool) > size:
        pool = pool.iloc[np.sort(rng.choice(len(pool), size, replace=False))]
    return st.Reference.from_frame(pool, part.numeric, part.categorical)


def _proportion(ref: st.Reference, frame: pd.DataFrame, alpha: float) -> float:
    return float(st.changed_features(st.window_feature_pvalues(ref, frame), alpha).mean())


def rolling_windows(w: int, lookback: int = LOOKBACK, gap: int = GAP) -> list[int]:
    """Reference windows of window ``w`` (empty if the history is too short)."""
    last = w - gap
    first = last - lookback + 1
    return list(range(first, last + 1)) if first >= 0 else []


def rolling_proportions(
    part: ex.Partition,
    idx: np.ndarray,
    s: ex.Settings,
    lookback: int = LOOKBACK,
    gap: int = GAP,
    seed: int = 0,
) -> np.ndarray:
    """Changed-feature proportion of every window against its rolling reference."""
    frames = window_frames(part, idx, s.window_size)
    out = np.zeros(len(frames))
    for w in range(len(frames)):
        ref_windows = rolling_windows(w, lookback, gap)
        if not ref_windows:
            continue
        rng = np.random.default_rng([seed, w])
        ref = reference_from_windows(frames, ref_windows, part, s.a_reference_size, rng)
        out[w] = _proportion(ref, frames[w], s.a_alpha)
    return out


def healthy_windows(monitored: pd.DataFrame, by_time: int) -> list[int]:
    """Windows that B has judged healthy once the labels released by ``by_time`` are in."""
    ok = monitored[
        monitored["eligible_eval"].astype(bool)
        & ~monitored["flagged"].astype(bool)
        & (monitored["available_at"] <= by_time)
    ]
    windows: set[int] = set()
    for first, last in zip(ok["first"], ok["last"], strict=True):
        windows.update(range(int(first), int(last) + 1))
    return sorted(windows)


def anchored_proportions(
    part: ex.Partition,
    idx: np.ndarray,
    s: ex.Settings,
    monitored: pd.DataFrame,
    lookback: int = LOOKBACK,
    seed: int = 0,
) -> np.ndarray:
    """Changed-feature proportions against the most recent B-healthy windows."""
    frames = window_frames(part, idx, s.window_size)
    out = np.zeros(len(frames))
    cache: dict[tuple[int, ...], st.Reference] = {}
    for w in range(len(frames)):
        healthy = [h for h in healthy_windows(monitored, w) if h < w]
        if len(healthy) < lookback:
            continue
        key = tuple(healthy[-lookback:])
        if key not in cache:
            rng = np.random.default_rng([seed, *key])
            cache[key] = reference_from_windows(frames, key, part, s.a_reference_size, rng)
        out[w] = _proportion(cache[key], frames[w], s.a_alpha)
    return out


# ----------------------------------------------------------------------------
# Calibration on validation (D21: same procedure as D10 and D11)
# ----------------------------------------------------------------------------


def _b_monitored(part, idx, cond, cal, s, seed) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(cohorts, B-monitored cohorts) for one label draw."""
    cohorts = ex._cohorts(part, idx, cond, cal, s, seed)
    return cohorts, st.b_monitor(cohorts, ex._b_rule(cal, s, "f1_calibrated"))


def _condition(name: str, s: ex.Settings) -> ex.Condition:
    return next(c for c in ex.label_conditions(s) if c.name == name)


def calibrate(
    pool: ex.Partition,
    scenarios: list[sc.Scenario],
    cal: ex.Calibration,
    s: ex.Settings,
    progress: bool = True,
    lookback: int = LOOKBACK,
    gap: int = GAP,
) -> RollingCalibration:
    """q for A_rolling and A_anchored on stable streams; L per delay on harmful streams.

    Uses the same calibration streams (seeds) as :func:`nadmon.experiment.calibrate`.
    """
    rc = RollingCalibration(lookback=lookback, gap=gap)
    index = sc.stratum_index(pool.strata)
    by_name = {x.name: x for x in scenarios}
    anchored_cond = _condition(ANCHORED_CALIBRATION, s)
    roll, anch = [], []
    for k in range(s.n_calibration):
        idx = sc.build_stream(
            by_name["S0_stable"],
            index,
            ex._stream_rng(s, 0, k, salt=1),
            s.window_size,
            s.n_windows,
            s.onset,
        )
        roll.append(rolling_proportions(pool, idx, s, rc.lookback, rc.gap, seed=k))
        _, monitored = _b_monitored(pool, idx, anchored_cond, cal, s, 7 + k)
        anch.append(anchored_proportions(pool, idx, s, monitored, rc.lookback, seed=k))
        if progress and (k + 1) % 20 == 0:
            print(f"  calibration S0 streams: {k + 1}/{s.n_calibration}")
    rc.q_rolling = st.calibrate_q(roll, s.target_false_warning, s.a_consecutive)
    rc.q_anchored = st.calibrate_q(anch, s.target_false_warning, s.a_consecutive)

    gaps: dict[int, list[int]] = {d: [] for d in s.delays}
    harmful = [x for x in scenarios if x.intended == "harmful"]
    conds = [c for c in ex.label_conditions(s) if c.mode == "random"]
    for j, scen in enumerate(harmful, start=1):
        for k in range(s.n_calibration):
            idx = sc.build_stream(
                scen, index, ex._stream_rng(s, j, k, salt=2), s.window_size, s.n_windows, s.onset
            )
            props = rolling_proportions(pool, idx, s, rc.lookback, rc.gap, seed=k)
            warnings = [
                w for w in st.a_warnings(props, rc.q_rolling, s.a_consecutive) if w >= s.onset
            ]
            if not warnings:
                continue
            for c, cond in enumerate(conds):
                cohorts = ex._cohorts(pool, idx, cond, cal, s, 7 + 1000 * (c + 1) + k)
                data, times = ex._alarms(st.b_monitor(cohorts, ex._b_rule(cal, s, "f1_calibrated")))
                true = [
                    t for d, t in zip(data, times, strict=True) if d >= s.onset and t >= warnings[0]
                ]
                if true:
                    gaps[cond.delay].append(true[0] - warnings[0])
            if progress and (k + 1) % 20 == 0:
                print(f"  calibration {scen.name} streams: {k + 1}/{s.n_calibration}")
    for d in s.delays:
        if gaps[d]:
            rc.periods[d] = max(st.calibrate_association(gaps[d], s.association_quantile), 1)
        else:
            rc.periods[d] = st.association_period(d)
        rc.association_gaps[d] = len(gaps[d])
    return rc


# ----------------------------------------------------------------------------
# Grid and time-ordered windows
# ----------------------------------------------------------------------------


def run_stream(
    part: ex.Partition,
    idx: np.ndarray,
    scenario: sc.Scenario,
    stream: int,
    conditions: list[ex.Condition],
    cal: ex.Calibration,
    rc: RollingCalibration,
    s: ex.Settings,
    seed: int,
) -> list[dict]:
    """A_rolling, A_anchored, B and C_active_rolling on one stream.

    Label draws use the same seeds as :func:`nadmon.experiment.run_stream`, so B's rows
    equal those of the earlier strategy runs.
    """
    harmful = scenario.intended == "harmful"
    base = {"scenario": scenario.name, "harmful": harmful, "stream": stream}
    rule = ex._b_rule(cal, s, "f1_calibrated")
    props = rolling_proportions(part, idx, s, rc.lookback, rc.gap, seed=seed)
    warnings = st.a_warnings(props, rc.q_rolling, s.a_consecutive)
    rows = [
        {
            **base,
            "strategy": "A_rolling",
            "condition": "inputs",
            **ev.score_events(warnings, warnings, s.onset, harmful),
        }
    ]
    for k, cond in enumerate(conditions):
        cohorts = ex._cohorts(part, idx, cond, cal, s, seed + 1000 * (k + 1))
        monitored = st.b_monitor(cohorts, rule)
        cbase = {**base, "condition": cond.name, "delay": cond.delay}
        data, times = ex._alarms(monitored)
        rows.append({**cbase, "strategy": "B", **ev.score_events(data, times, s.onset, harmful)})
        period = rc.periods.get(cond.delay, st.association_period(cond.delay))
        data, times = ex._alarms(st.c_active(cohorts, rule, warnings, period))
        rows.append(
            {
                **cbase,
                "strategy": "C_active_rolling",
                **ev.score_events(data, times, s.onset, harmful),
            }
        )
        if cond.name in ANCHORED_CONDITIONS:
            anch = anchored_proportions(part, idx, s, monitored, rc.lookback, seed=seed)
            aw = st.a_warnings(anch, rc.q_anchored, s.a_consecutive)
            rows.append(
                {
                    **cbase,
                    "strategy": "A_anchored",
                    **ev.score_events(aw, aw, s.onset, harmful),
                    "judged_windows": int((anch > 0).sum()),
                }
            )
    return rows


def run_grid(
    part: ex.Partition,
    scenarios: list[sc.Scenario],
    cal: ex.Calibration,
    rc: RollingCalibration,
    s: ex.Settings,
    progress: bool = True,
    on_scenario: Callable[[str], None] | None = None,
) -> pd.DataFrame:
    """Every scenario x stream x label condition, with the streams of the earlier runs."""
    index = sc.stratum_index(part.strata)
    conditions = ex.label_conditions(s)
    rows = []
    for j, scen in enumerate(scenarios):
        for k in range(s.n_streams):
            rng = ex._stream_rng(s, j, k, salt=3)
            idx = sc.build_stream(scen, index, rng, s.window_size, s.n_windows, s.onset)
            seed = int(rng.integers(0, 2**31 - 1))
            rows += run_stream(part, idx, scen, k, conditions, cal, rc, s, seed)
            if progress and (k + 1) % 25 == 0:
                print(f"  {scen.name}: {k + 1}/{s.n_streams} streams")
        if on_scenario:
            on_scenario(scen.name)
    return pd.DataFrame(rows)


def run_natural(
    part: ex.Partition,
    cal: ex.Calibration,
    rc: RollingCalibration,
    s: ex.Settings,
    seed: int = 0,
) -> pd.DataFrame:
    """A_rolling and C_active_rolling on the partition's real windows in time order."""
    W = s.window_size
    n = len(part.y) // W
    idx = np.arange(n * W)
    props = rolling_proportions(part, idx, s, rc.lookback, rc.gap, seed=seed)
    judged = props[[bool(rolling_windows(w, rc.lookback, rc.gap)) for w in range(n)]]
    warnings = st.a_warnings(props, rc.q_rolling, s.a_consecutive)
    rows = [
        {
            "strategy": "A_rolling",
            "condition": "inputs",
            "windows": n,
            "alarms": len(warnings),
            "alarm_windows": " ".join(str(w + 1) for w in warnings),
            "flagged_window_share": float(np.mean(judged >= rc.q_rolling)),
            "median_changed_proportion": float(np.median(judged)),
        }
    ]
    rule = ex._b_rule(cal, s, "f1_calibrated")
    for k, cond in enumerate(ex.label_conditions(s)):
        if cond.mode != "random":
            continue
        cohorts = ex._cohorts(part, idx, cond, cal, s, seed + 1000 * (k + 1))
        period = rc.periods.get(cond.delay, st.association_period(cond.delay))
        for name, m in (
            ("B", st.b_monitor(cohorts, rule)),
            ("C_active_rolling", st.c_active(cohorts, rule, warnings, period)),
        ):
            data, times = ex._alarms(m)
            rows.append(
                {
                    "strategy": name,
                    "condition": cond.name,
                    "windows": n,
                    "alarms": len(times),
                    "alarm_windows": " ".join(str(t + 1) for t in times),
                }
            )
    return pd.DataFrame(rows)
