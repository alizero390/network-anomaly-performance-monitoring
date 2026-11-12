import numpy as np
import pandas as pd
import pytest

from nadmon import labels as lb
from nadmon import strategies as st

# ---------------------------------------------------------------------------
# Strategy A
# ---------------------------------------------------------------------------


def _frame(rng, n, shift=0.0, cat_p=(0.6, 0.3, 0.1)):
    return pd.DataFrame(
        {
            "x1": rng.normal(shift, 1, n),
            "x2": rng.exponential(1, n),
            "proto": rng.choice(["tcp", "udp", "icmp"], n, p=list(cat_p)),
        }
    )


def test_chi_square_merges_sparse_and_unseen_categories():
    ref = pd.Series(["a"] * 500 + ["b"] * 500 + ["rare"] * 2).value_counts()
    same = pd.Series(["a"] * 50 + ["b"] * 50)
    assert st.chi_square_p(ref, same) > 0.05
    new = pd.Series(["a"] * 20 + ["zzz"] * 80)  # unseen category
    assert st.chi_square_p(ref, new) < 1e-6
    assert st.chi_square_p(pd.Series({"a": 100}), pd.Series(["a"] * 10)) == 1.0


def test_strategy_a_flags_shift_not_noise():
    rng = np.random.default_rng(0)
    ref = st.Reference.from_frame(_frame(rng, 20000), ["x1", "x2"], ["proto"])
    stable = [_frame(rng, 2000) for _ in range(5)]
    shifted = [_frame(rng, 2000, shift=0.5, cat_p=(0.3, 0.3, 0.4)) for _ in range(5)]
    p_stable = st.changed_proportion(ref, stable)
    p_shift = st.changed_proportion(ref, shifted)
    assert p_stable.max() <= 1 / 3
    assert (p_shift >= 2 / 3).all()


def test_bh_correction():
    p = pd.Series([0.001, 0.02, 0.5], index=["a", "b", "c"])
    assert st.changed_features(p, alpha=0.01).tolist() == [True, False, False]
    assert st.changed_features(p, alpha=0.05).tolist() == [True, True, False]


def test_run_warnings_need_consecutive_and_fresh_run():
    flags = [0, 1, 0, 1, 1, 1, 1, 0, 1, 1]
    assert st.run_warnings(np.array(flags), 2) == [4, 9]
    assert st.run_warnings(np.array(flags), 1) == [1, 3, 8]


def test_calibrate_q_meets_target():
    rng = np.random.default_rng(1)
    streams = [rng.choice([0, 0, 0, 0.1, 0.2], size=40) for _ in range(100)]
    q = st.calibrate_q(streams, target_rate=0.05)
    rate = np.mean([len(st.a_warnings(s, q)) > 0 for s in streams])
    assert rate <= 0.05


# ---------------------------------------------------------------------------
# Strategy B
# ---------------------------------------------------------------------------


def _cohorts(recalls, fprs=None, attacks=1000, normals=4000, delay=0, eligible=None):
    n = len(recalls)
    fprs = fprs if fprs is not None else [0.005] * n
    tp = np.round(np.array(recalls) * attacks).astype(int)
    fp = np.round(np.array(fprs) * normals).astype(int)
    return pd.DataFrame(
        {
            "first": range(n),
            "last": range(n),
            "span": 1,
            "tp": tp,
            "fn": attacks - tp,
            "fp": fp,
            "tn": normals - fp,
            "attacks": attacks,
            "normals": normals,
            "eligible": eligible if eligible is not None else [True] * n,
            "available_at": [i + delay for i in range(n)],
        }
    )


def test_cohort_metric_calibrated_ignores_share():
    a = _cohorts([0.95], attacks=1000, normals=4000)
    b = _cohorts([0.95], attacks=100, normals=8000)
    va = st.cohort_metric(a, "f1_calibrated", 0.2)
    vb = st.cohort_metric(b, "f1_calibrated", 0.2)
    assert va[0] == pytest.approx(vb[0], abs=1e-9)
    assert st.cohort_metric(b, "f1", 0.2)[0] < st.cohort_metric(a, "f1", 0.2)[0] - 0.05
    with pytest.raises(ValueError):
        st.cohort_metric(a, "mcc", 0.2)


def test_b_alarm_needs_two_consecutive_and_rearms():
    rule = st.BRule(reference=0.97, reference_share=0.2)
    rec = [0.97, 0.7, 0.97, 0.7, 0.7, 0.7, 0.97, 0.97, 0.7, 0.7]
    m = st.b_monitor(_cohorts(rec), rule)
    assert st.b_alarm_times(m) == [4, 9]  # one alarm per event; re-armed after 2 calm


def test_b_skips_ineligible_without_breaking_run():
    rule = st.BRule(reference=0.97, reference_share=0.2)
    m = st.b_monitor(_cohorts([0.7, 0.97, 0.7], eligible=[True, False, True]), rule)
    assert st.b_alarm_times(m) == [2]


def test_b_alarm_time_includes_delay():
    rule = st.BRule(reference=0.97, reference_share=0.2)
    m = st.b_monitor(_cohorts([0.97, 0.7, 0.7], delay=5), rule)
    assert st.b_alarm_times(m) == [7]


def test_b_detects_false_positive_burst_with_calibrated_f1():
    rule = st.BRule(reference=0.97, reference_share=0.2)
    m = st.b_monitor(_cohorts([0.97] * 4, fprs=[0.005, 0.06, 0.06, 0.005]), rule)
    assert st.b_alarm_times(m) == [2]


def test_b_works_with_pooled_cohorts():
    rng = np.random.default_rng(3)
    y = (rng.random(50_000) < 0.02).astype(int)
    p = np.where(y == 1, rng.random(50_000) < 0.95, rng.random(50_000) < 0.005).astype(int)
    mask = lb.label_mask(len(y), 0.2, seed=1)
    cohorts = lb.pool_cohorts(lb.cohort_counts(y, p, mask, 5000), lb.PoolingRule(68), delay=0)
    m = st.b_monitor(cohorts, st.BRule(reference=0.97, reference_share=0.2))
    assert m["span"].max() > 1
    assert not m["alarm"].any()


# ---------------------------------------------------------------------------
# Strategy C
# ---------------------------------------------------------------------------


def test_classify_warnings():
    w, a = st.classify_warnings([3, 20], [6, 30], period=5)
    assert w["confirmed"].tolist() == [True, False]
    assert w["lead_time"].tolist()[0] == 3
    assert a["preceded_by_warning"].tolist() == [True, False]


def test_c_active_confirms_earlier_during_warning():
    rule = st.BRule(reference=0.97, reference_share=0.2)
    cohorts = _cohorts([0.97, 0.97, 0.7, 0.7, 0.7])
    assert st.b_alarm_times(st.b_monitor(cohorts, rule)) == [3]
    assert st.b_alarm_times(st.c_active(cohorts, rule, warnings=[1], period=5)) == [2]
    # outside the association period the normal rule applies
    assert st.b_alarm_times(st.c_active(cohorts, rule, warnings=[-10], period=5)) == [3]


def test_association_helpers():
    assert st.association_period(5) == 10
    assert st.calibrate_association([1, 2, 3, 4, 10], quantile=0.8) == 4
    with pytest.raises(ValueError):
        st.calibrate_association([])
