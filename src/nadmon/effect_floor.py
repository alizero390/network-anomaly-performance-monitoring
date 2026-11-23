"""Strategy A with a minimum effect size (decision D22).

On real windows in time order, A with a rolling reference (D21) flagged every window:
with 5,000 records per window the tests find differences too small to matter. D22 counts
a feature as changed only if its Benjamini-Hochberg adjusted p-value is at most ``alpha``
**and** its effect size is at least a floor ``epsilon``: the Kolmogorov-Smirnov statistic
(numeric) or the total variation distance of the category mix (categorical).

Calibration on validation only:

1. ``epsilon``: the smallest value of :data:`EPSILON_GRID` for which at most 5% of the
   judged real validation windows (time order, rolling reference) have a changed-feature
   proportion at or above D21's ``q``; the largest grid value if none qualifies.
2. ``q``: recalibrated with that ``epsilon`` on the stable validation streams of D21
   (at most 5% with a warning, two consecutive windows).
3. Everything else from D21 unchanged: reference windows ``w-14..w-5``, a reference
   sample of 20,000 records, the association periods L of C_active_rolling.

Variants: **A_floor** and **C_active_floor** (C active with A_floor's warnings).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from nadmon import evaluation as ev
from nadmon import experiment as ex
from nadmon import rolling_a as ra
from nadmon import scenarios as sc
from nadmon import strategies as st

EPSILON_GRID = (0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30)
TARGET_REAL_WINDOWS = 0.05
STRATEGIES = ("A_floor", "B", "C_active_floor")


@dataclass
class FloorCalibration:
    epsilon: float | None = None
    q: float | None = None
    lookback: int = ra.LOOKBACK
    gap: int = ra.GAP
    periods: dict[int, int] = field(default_factory=dict)
    real_window_share: dict[float, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["real_window_share"] = {str(k): v for k, v in self.real_window_share.items()}
        return d


def rolling_tests(
    part: ex.Partition,
    idx: np.ndarray,
    s: ex.Settings,
    lookback: int = ra.LOOKBACK,
    gap: int = ra.GAP,
    seed: int = 0,
) -> list[pd.DataFrame | None]:
    """p-values and effect sizes of every window against its rolling reference.

    The reference samples equal those of :func:`nadmon.rolling_a.rolling_proportions`
    (same seeds); windows without a full reference get ``None``.
    """
    frames = ra.window_frames(part, idx, s.window_size)
    out: list[pd.DataFrame | None] = []
    for w in range(len(frames)):
        ref_windows = ra.rolling_windows(w, lookback, gap)
        if not ref_windows:
            out.append(None)
            continue
        rng = np.random.default_rng([seed, w])
        ref = ra.reference_from_windows(frames, ref_windows, part, s.a_reference_size, rng)
        out.append(st.window_feature_tests(ref, frames[w]))
    return out


def proportions(tests: list[pd.DataFrame | None], alpha: float, floor: float) -> np.ndarray:
    """Changed-feature proportion per window; 0 where the window is not judged."""
    return np.array(
        [
            0.0 if t is None else float(st.changed_features_floor(t, alpha, floor).mean())
            for t in tests
        ]
    )


def real_window_share(tests, alpha: float, floor: float, q: float) -> float:
    judged = [t for t in tests if t is not None]
    if not judged:
        return 0.0
    return float(np.mean(proportions(judged, alpha, floor) >= q))


def choose_epsilon(
    tests, alpha: float, q: float, grid=EPSILON_GRID, target: float = TARGET_REAL_WINDOWS
) -> tuple[float, dict[float, float]]:
    """Smallest grid value flagging at most ``target`` of the judged real windows."""
    shares = {eps: real_window_share(tests, alpha, eps, q) for eps in grid}
    for eps in sorted(grid):
        if shares[eps] <= target:
            return float(eps), shares
    return float(max(grid)), shares


def calibrate(
    part: ex.Partition,
    pool: ex.Partition,
    scenarios: list[sc.Scenario],
    s: ex.Settings,
    rolling: ra.RollingCalibration,
    progress: bool = True,
) -> FloorCalibration:
    """epsilon on the real validation windows, then q on stable validation streams.

    ``part`` is the whole validation partition in time order; ``pool`` the stream half;
    ``rolling`` the frozen D21 settings (q_rolling, lookback, gap, periods).
    """
    fc = FloorCalibration(lookback=rolling.lookback, gap=rolling.gap, periods=dict(rolling.periods))
    n = len(part.y) // s.window_size
    real = rolling_tests(part, np.arange(n * s.window_size), s, fc.lookback, fc.gap, seed=s.seed)
    fc.epsilon, fc.real_window_share = choose_epsilon(real, s.a_alpha, rolling.q_rolling)
    if progress:
        shares = ", ".join(f"{k:g}: {v:.0%}" for k, v in fc.real_window_share.items())
        print(f"  real validation windows flagged by epsilon: {shares}")
    index = sc.stratum_index(pool.strata)
    stable = next(x for x in scenarios if x.name == "S0_stable")
    props = []
    for k in range(s.n_calibration):
        idx = sc.build_stream(
            stable, index, ex._stream_rng(s, 0, k, salt=1), s.window_size, s.n_windows, s.onset
        )
        tests = rolling_tests(pool, idx, s, fc.lookback, fc.gap, seed=k)
        props.append(proportions(tests, s.a_alpha, fc.epsilon))
        if progress and (k + 1) % 20 == 0:
            print(f"  calibration S0 streams: {k + 1}/{s.n_calibration}")
    fc.q = st.calibrate_q(props, s.target_false_warning, s.a_consecutive)
    return fc


def run_stream(
    part: ex.Partition,
    idx: np.ndarray,
    scenario: sc.Scenario,
    stream: int,
    conditions: list[ex.Condition],
    cal: ex.Calibration,
    fc: FloorCalibration,
    s: ex.Settings,
    seed: int,
) -> list[dict]:
    """A_floor, B and C_active_floor on one stream (label draws as in D21)."""
    harmful = scenario.intended == "harmful"
    base = {"scenario": scenario.name, "harmful": harmful, "stream": stream}
    rule = ex._b_rule(cal, s, "f1_calibrated")
    tests = rolling_tests(part, idx, s, fc.lookback, fc.gap, seed=seed)
    warnings = st.a_warnings(proportions(tests, s.a_alpha, fc.epsilon), fc.q, s.a_consecutive)
    rows = [
        {
            **base,
            "strategy": "A_floor",
            "condition": "inputs",
            **ev.score_events(warnings, warnings, s.onset, harmful),
        }
    ]
    for k, cond in enumerate(conditions):
        cohorts = ex._cohorts(part, idx, cond, cal, s, seed + 1000 * (k + 1))
        cbase = {**base, "condition": cond.name, "delay": cond.delay}
        data, times = ex._alarms(st.b_monitor(cohorts, rule))
        rows.append({**cbase, "strategy": "B", **ev.score_events(data, times, s.onset, harmful)})
        period = fc.periods.get(cond.delay, st.association_period(cond.delay))
        data, times = ex._alarms(st.c_active(cohorts, rule, warnings, period))
        rows.append(
            {
                **cbase,
                "strategy": "C_active_floor",
                **ev.score_events(data, times, s.onset, harmful),
            }
        )
    return rows


def run_grid(
    part: ex.Partition,
    scenarios: list[sc.Scenario],
    cal: ex.Calibration,
    fc: FloorCalibration,
    s: ex.Settings,
    progress: bool = True,
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
            rows += run_stream(part, idx, scen, k, conditions, cal, fc, s, seed)
            if progress and (k + 1) % 25 == 0:
                print(f"  {scen.name}: {k + 1}/{s.n_streams} streams")
    return pd.DataFrame(rows)


def run_natural(
    part: ex.Partition, cal: ex.Calibration, fc: FloorCalibration, s: ex.Settings, seed: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A_floor and C_active_floor on the real windows in time order.

    Returns (alarms per strategy and condition, per-window table: proportion with and
    without the floor, and the features changed with the floor).
    """
    W = s.window_size
    n = len(part.y) // W
    idx = np.arange(n * W)
    tests = rolling_tests(part, idx, s, fc.lookback, fc.gap, seed=seed)
    props = proportions(tests, s.a_alpha, fc.epsilon)
    plain = proportions(tests, s.a_alpha, 0.0)
    warnings = st.a_warnings(props, fc.q, s.a_consecutive)
    judged = np.array([t is not None for t in tests])
    windows = pd.DataFrame(
        {
            "window": np.arange(1, n + 1),
            "judged": judged,
            "changed_proportion_floor": props,
            "changed_proportion_no_floor": plain,
            "flagged": judged & (props >= fc.q),
            "changed_features": [
                ""
                if t is None
                else " ".join(t.index[st.changed_features_floor(t, s.a_alpha, fc.epsilon)])
                for t in tests
            ],
        }
    )
    rows = [
        {
            "strategy": "A_floor",
            "condition": "inputs",
            "windows": n,
            "alarms": len(warnings),
            "alarm_windows": " ".join(str(w + 1) for w in warnings),
            "flagged_window_share": float(windows.loc[judged, "flagged"].mean()),
        }
    ]
    rule = ex._b_rule(cal, s, "f1_calibrated")
    for k, cond in enumerate(ex.label_conditions(s)):
        if cond.mode != "random":
            continue
        cohorts = ex._cohorts(part, idx, cond, cal, s, seed + 1000 * (k + 1))
        period = fc.periods.get(cond.delay, st.association_period(cond.delay))
        for name, m in (
            ("B", st.b_monitor(cohorts, rule)),
            ("C_active_floor", st.c_active(cohorts, rule, warnings, period)),
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
    return pd.DataFrame(rows), windows
