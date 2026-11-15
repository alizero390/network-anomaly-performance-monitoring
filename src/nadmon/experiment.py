"""Strategy comparison experiment (design spec D1, D3, D7-D14).

A :class:`Partition` holds one monitored partition: labels, frozen-model predictions,
strata and (for Strategy A) the model's input features, all in the same row order.
Validation is split at random in two halves (D10): one half supplies Strategy A's
reference sample, the other half the records that streams are drawn from.

Calibration (validation only, D1): Strategy A's threshold ``q`` from stable streams
(D10) and Strategy C's association period ``L`` per label delay from harmful streams
(D11). The calibrated values are then frozen and used unchanged on every stream.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from nadmon import evaluation as ev
from nadmon import labels as lb
from nadmon import scenarios as sc
from nadmon import strategies as st

STRATEGIES = (
    "A",
    "A_natural",
    "B_F1",
    "B",
    "B_ipw",
    "C_passive",
    "C_active",
    "C_active_natural",
)


@dataclass
class Partition:
    y: np.ndarray
    p: np.ndarray
    strata: np.ndarray
    features: pd.DataFrame | None = None
    numeric: tuple[str, ...] = ()
    categorical: tuple[str, ...] = ()

    def subset(self, idx: np.ndarray) -> Partition:
        return Partition(
            self.y[idx],
            self.p[idx],
            self.strata[idx],
            None if self.features is None else self.features.iloc[idx].reset_index(drop=True),
            self.numeric,
            self.categorical,
        )


@dataclass(frozen=True)
class Settings:
    window_size: int = 5000
    n_windows: int = 40
    onset: int = 20
    n_streams: int = 200
    n_calibration: int = 100
    seed: int = 20261112
    delays: tuple[int, ...] = (0, 5, 10)
    availabilities: tuple[float, ...] = (1.0, 0.5, 0.2)
    alert_first_delay: int = 5
    m_min: int = 500
    max_span: int = 5
    a_alpha: float = 0.01
    a_consecutive: int = 2
    a_reference_size: int = 20_000
    target_false_warning: float = 0.05
    association_quantile: float = 0.95
    drop: float = 0.05
    consecutive: int = 2
    rearm: int = 2
    ipw_effective: bool = False  # also run B_ipw_eff (label-bias study, D17)


@dataclass
class Calibration:
    pi0: float
    recall: float
    n_min: int
    reference_f1_calibrated: float
    reference_f1: float
    q: float | None = None
    q_natural: float | None = None
    periods: dict[int, int] = field(default_factory=dict)
    association_gaps: dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Condition:
    """A label-feedback condition.

    ``mode="random"`` labels every record with ``availability``. ``mode="alert_first"``
    labels predicted attacks with ``p_alert`` and predicted normal records with
    ``p_normal``. B_ipw weights by ``assumed_p_alert`` / ``assumed_p_normal`` when given
    (to study wrongly known probabilities), otherwise by the true ones.
    """

    name: str
    delay: int
    availability: float
    mode: str = "random"
    p_alert: float = lb.P_ALERT
    p_normal: float = lb.P_NORMAL
    assumed_p_alert: float | None = None
    assumed_p_normal: float | None = None


def label_conditions(s: Settings) -> list[Condition]:
    out = [Condition(f"d{d}_p{round(a * 100)}", d, a) for d in s.delays for a in s.availabilities]
    out.append(
        Condition(f"d{s.alert_first_delay}_alert_first", s.alert_first_delay, 1.0, "alert_first")
    )
    return out


def split_validation(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Random halves: (Strategy A reference records, stream records)."""
    perm = np.random.default_rng(seed).permutation(n)
    return np.sort(perm[: n // 2]), np.sort(perm[n // 2 :])


def base_calibration(validation: Partition) -> Calibration:
    """Reference values from the whole validation partition (D6, D8)."""
    y, p = validation.y, validation.p
    tp = int(((y == 1) & (p == 1)).sum())
    fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum())
    recall = tp / (tp + fn)
    fpr = fp / int((y == 0).sum())
    pi0 = float(y.mean())
    return Calibration(
        pi0=pi0,
        recall=recall,
        n_min=lb.n_min_for_recall(recall),
        reference_f1_calibrated=float(st.calibrated_f1(recall, fpr, pi0)),
        reference_f1=2 * tp / (2 * tp + fp + fn),
    )


def a_reference(part: Partition, s: Settings) -> st.Reference | None:
    if part.features is None:
        return None
    rng = np.random.default_rng(s.seed + 1)
    n = min(s.a_reference_size, len(part.features))
    sample = part.features.iloc[np.sort(rng.choice(len(part.features), n, replace=False))]
    return st.Reference.from_frame(sample, part.numeric, part.categorical)


def _stream_rng(s: Settings, scenario_no: int, stream: int, salt: int = 0) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([s.seed, salt, scenario_no, stream]))


def a_proportions(part: Partition, idx: np.ndarray, ref: st.Reference, s: Settings) -> np.ndarray:
    W = s.window_size
    windows = [part.features.iloc[idx[w * W : (w + 1) * W]] for w in range(len(idx) // W)]
    return st.changed_proportion(ref, windows, s.a_alpha)


def _b_rule(cal: Calibration, s: Settings, metric: str) -> st.BRule:
    ref = cal.reference_f1_calibrated if metric == "f1_calibrated" else cal.reference_f1
    return st.BRule(
        reference=ref,
        metric=metric,
        reference_share=cal.pi0,
        drop=s.drop,
        consecutive=s.consecutive,
        rearm=s.rearm,
    )


def _window_counts(part, idx, cond: Condition, s: Settings, seed: int) -> pd.DataFrame:
    """Labelled confusion counts per window under the condition's labelling policy."""
    y, p = part.y[idx], part.p[idx]
    mask = lb.label_mask(
        len(idx),
        cond.availability,
        seed=seed,
        mode=cond.mode,
        y_pred=p,
        p_alert=cond.p_alert,
        p_normal=cond.p_normal,
    )
    return lb.cohort_counts(y, p, mask, s.window_size)


def _pool(counts: pd.DataFrame, cond: Condition, cal: Calibration, s: Settings) -> pd.DataFrame:
    return lb.pool_cohorts(counts, lb.PoolingRule(cal.n_min, s.m_min, s.max_span), cond.delay)


def _cohorts(part, idx, cond: Condition, cal: Calibration, s: Settings, seed: int):
    return _pool(_window_counts(part, idx, cond, s, seed), cond, cal, s)


def _ipw(cohorts: pd.DataFrame, cond: Condition) -> pd.DataFrame:
    """Weighted cohorts for B_ipw; the weights follow the condition's labelling policy."""
    if cond.mode == "alert_first":
        pa = cond.p_alert if cond.assumed_p_alert is None else cond.assumed_p_alert
        pn = cond.p_normal if cond.assumed_p_normal is None else cond.assumed_p_normal
        return lb.ipw_cohorts(cohorts, pa, pn)
    return lb.ipw_cohorts(cohorts, cond.availability, cond.availability)


def _alarms(monitored: pd.DataFrame) -> tuple[list[int], list[int]]:
    a = monitored[monitored["alarm"]]
    return a["last"].astype(int).tolist(), a["available_at"].astype(int).tolist()


def run_stream(
    part: Partition,
    idx: np.ndarray,
    scenario: sc.Scenario,
    stream: int,
    conditions: list[Condition],
    cal: Calibration,
    s: Settings,
    ref: st.Reference | None,
    seed: int,
) -> list[dict]:
    """All strategies and label conditions on one stream; one row per (strategy, condition)."""
    harmful = scenario.intended == "harmful"
    base = {"scenario": scenario.name, "harmful": harmful, "stream": stream}
    rows = []
    warnings = warnings_nat = None
    if ref is not None and cal.q is not None:
        props = a_proportions(part, idx, ref, s)
        warnings = st.a_warnings(props, cal.q, s.a_consecutive)
        score = ev.score_events(warnings, warnings, s.onset, harmful)
        rows.append({**base, "strategy": "A", "condition": "inputs", **score})
        if cal.q_natural is not None:
            warnings_nat = st.a_warnings(props, cal.q_natural, s.a_consecutive)
            score = ev.score_events(warnings_nat, warnings_nat, s.onset, harmful)
            rows.append({**base, "strategy": "A_natural", "condition": "inputs", **score})
    for k, cond in enumerate(conditions):
        counts = _window_counts(part, idx, cond, s, seed + 1000 * (k + 1))
        cohorts = _pool(counts, cond, cal, s)
        cbase = {**base, "condition": cond.name, "delay": cond.delay}
        b_alarms = {}
        variants = [
            ("B_F1", "f1", cohorts),
            ("B", "f1_calibrated", cohorts),
            ("B_ipw", "f1_calibrated", _ipw(cohorts, cond)),
        ]
        if s.ipw_effective:
            # Weight first, then pool and check eligibility on the weighted counts.
            variants.append(("B_ipw_eff", "f1_calibrated", _pool(_ipw(counts, cond), cond, cal, s)))
        for name, metric, data_ in variants:
            b_alarms[name] = _alarms(st.b_monitor(data_, _b_rule(cal, s, metric)))
            data, times = b_alarms[name]
            rows.append(
                {**cbase, "strategy": name, **ev.score_events(data, times, s.onset, harmful)}
            )
        if warnings is None:
            continue
        period = cal.periods.get(cond.delay, st.association_period(cond.delay))
        data, times = b_alarms["B"]
        score = ev.score_events(data, times, s.onset, harmful)
        true_times = [t for d, t in zip(data, times, strict=True) if d >= s.onset and harmful]
        warned, lead = False, np.nan
        if true_times:
            first = true_times[0]
            before = [w for w in warnings if first - period <= w <= first]
            warned = bool(before)
            lead = float(first - before[-1]) if before else np.nan
        post_warnings = [w for w in warnings if w >= s.onset]
        warning_table, _ = st.classify_warnings(post_warnings, times, period)
        rows.append(
            {
                **cbase,
                "strategy": "C_passive",
                **score,
                "warned_before_alarm": warned,
                "lead_time": lead,
                "unconfirmed_warnings": int((~warning_table["confirmed"].astype(bool)).sum()),
            }
        )
        data, times = _alarms(
            st.c_active(cohorts, _b_rule(cal, s, "f1_calibrated"), warnings, period)
        )
        rows.append(
            {**cbase, "strategy": "C_active", **ev.score_events(data, times, s.onset, harmful)}
        )
        if warnings_nat is not None:
            data, times = _alarms(
                st.c_active(cohorts, _b_rule(cal, s, "f1_calibrated"), warnings_nat, period)
            )
            rows.append(
                {
                    **cbase,
                    "strategy": "C_active_natural",
                    **ev.score_events(data, times, s.onset, harmful),
                }
            )
    return rows


def calibrate(
    pool: Partition,
    scenarios: list[sc.Scenario],
    cal: Calibration,
    s: Settings,
    ref: st.Reference | None,
    progress: bool = True,
    natural: Partition | None = None,
) -> Calibration:
    """Fill ``cal.q`` (D10) and ``cal.periods`` (D11) from validation streams.

    With ``natural`` (the validation partition in time order), also ``cal.q_natural``:
    the threshold flagging at most ``target_false_warning`` of the real windows.
    """
    if ref is None:
        return cal
    if natural is not None:
        W = s.window_size
        n = len(natural.y) // W
        props_nat = a_proportions(natural, np.arange(n * W), ref, s)
        cal.q_natural = st.calibrate_q_windows(props_nat, s.target_false_warning)
    index = sc.stratum_index(pool.strata)
    by_name = {x.name: x for x in scenarios}
    stable = by_name["S0_stable"]
    props = []
    for k in range(s.n_calibration):
        idx = sc.build_stream(
            stable, index, _stream_rng(s, 0, k, salt=1), s.window_size, s.n_windows, s.onset
        )
        props.append(a_proportions(pool, idx, ref, s))
        if progress and (k + 1) % 20 == 0:
            print(f"  calibration S0 streams: {k + 1}/{s.n_calibration}")
    cal.q = st.calibrate_q(props, s.target_false_warning, s.a_consecutive)

    gaps: dict[int, list[int]] = {d: [] for d in s.delays}
    harmful = [x for x in scenarios if x.intended == "harmful"]
    conds = [c for c in label_conditions(s) if c.mode == "random"]
    for j, scen in enumerate(harmful, start=1):
        for k in range(s.n_calibration):
            idx = sc.build_stream(
                scen, index, _stream_rng(s, j, k, salt=2), s.window_size, s.n_windows, s.onset
            )
            warnings = [
                w
                for w in st.a_warnings(a_proportions(pool, idx, ref, s), cal.q, s.a_consecutive)
                if w >= s.onset
            ]
            if not warnings:
                continue
            for c, cond in enumerate(conds):
                cohorts = _cohorts(pool, idx, cond, cal, s, 7 + 1000 * (c + 1) + k)
                data, times = _alarms(st.b_monitor(cohorts, _b_rule(cal, s, "f1_calibrated")))
                true = [
                    t for d, t in zip(data, times, strict=True) if d >= s.onset and t >= warnings[0]
                ]
                if true:
                    gaps[cond.delay].append(true[0] - warnings[0])
            if progress and (k + 1) % 20 == 0:
                print(f"  calibration {scen.name} streams: {k + 1}/{s.n_calibration}")
    for d in s.delays:
        if gaps[d]:
            cal.periods[d] = max(st.calibrate_association(gaps[d], s.association_quantile), 1)
        else:
            cal.periods[d] = st.association_period(d)
        cal.association_gaps[d] = len(gaps[d])
    return cal


def run_grid(
    pool: Partition,
    scenarios: list[sc.Scenario],
    cal: Calibration,
    s: Settings,
    ref: st.Reference | None,
    progress: bool = True,
    conditions: list[Condition] | None = None,
) -> pd.DataFrame:
    """Every scenario x stream x label condition x strategy (D14).

    ``conditions`` defaults to :func:`label_conditions`; the label-bias study passes its
    own policy grid (D17).
    """
    index = sc.stratum_index(pool.strata)
    conditions = label_conditions(s) if conditions is None else conditions
    rows = []
    for j, scen in enumerate(scenarios):
        for k in range(s.n_streams):
            rng = _stream_rng(s, j, k, salt=3)
            idx = sc.build_stream(scen, index, rng, s.window_size, s.n_windows, s.onset)
            seed = int(rng.integers(0, 2**31 - 1))
            rows += run_stream(pool, idx, scen, k, conditions, cal, s, ref, seed)
            if progress and (k + 1) % 25 == 0:
                print(f"  {scen.name}: {k + 1}/{s.n_streams} streams")
    return pd.DataFrame(rows)


def run_natural(
    part: Partition, cal: Calibration, s: Settings, ref: st.Reference | None, seed: int = 0
) -> pd.DataFrame:
    """All strategies on the partition's own windows in time order (no injected change).

    There is no ground truth here: every alarm is reported with its window. Returns one
    row per (strategy, condition): alarms, alarm windows, and for A the share of windows
    flagged.
    """
    W = s.window_size
    n = len(part.y) // W
    idx = np.arange(n * W)
    rows = []
    warnings = None
    if ref is not None and cal.q is not None:
        props = a_proportions(part, idx, ref, s)
        warnings = st.a_warnings(props, cal.q, s.a_consecutive)
        rows.append(
            {
                "strategy": "A",
                "condition": "inputs",
                "windows": n,
                "alarms": len(warnings),
                "alarm_windows": " ".join(str(w + 1) for w in warnings),
                "flagged_window_share": float(np.mean(props >= cal.q)),
                "median_changed_proportion": float(np.median(props)),
            }
        )
    warnings_nat = None
    if warnings is not None and cal.q_natural is not None:
        warnings_nat = st.a_warnings(props, cal.q_natural, s.a_consecutive)
        rows.append(
            {
                "strategy": "A_natural",
                "condition": "inputs",
                "windows": n,
                "alarms": len(warnings_nat),
                "alarm_windows": " ".join(str(w + 1) for w in warnings_nat),
                "flagged_window_share": float(np.mean(props >= cal.q_natural)),
                "median_changed_proportion": float(np.median(props)),
            }
        )
    for k, cond in enumerate(label_conditions(s)):
        cohorts = _cohorts(part, idx, cond, cal, s, seed + 1000 * (k + 1))
        runs = {
            "B_F1": st.b_monitor(cohorts, _b_rule(cal, s, "f1")),
            "B": st.b_monitor(cohorts, _b_rule(cal, s, "f1_calibrated")),
            "B_ipw": st.b_monitor(_ipw(cohorts, cond), _b_rule(cal, s, "f1_calibrated")),
        }
        period = cal.periods.get(cond.delay, st.association_period(cond.delay))
        if warnings is not None:
            runs["C_active"] = st.c_active(
                cohorts, _b_rule(cal, s, "f1_calibrated"), warnings, period
            )
        if warnings_nat is not None:
            runs["C_active_natural"] = st.c_active(
                cohorts, _b_rule(cal, s, "f1_calibrated"), warnings_nat, period
            )
        for name, m in runs.items():
            data, times = _alarms(m)
            rows.append(
                {
                    "strategy": name,
                    "condition": cond.name,
                    "windows": n,
                    "alarms": len(times),
                    "alarm_windows": " ".join(str(d + 1) for d in data),
                }
            )
    return pd.DataFrame(rows)
