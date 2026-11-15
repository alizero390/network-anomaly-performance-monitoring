import numpy as np
import pytest

from nadmon import labels as lb


def test_n_min_matches_spec_value_for_feb_rf():
    assert lb.n_min_for_recall(0.968) == 68
    assert lb.n_min_for_recall(1.0) == 1
    with pytest.raises(ValueError):
        lb.n_min_for_recall(1.5)


def test_random_mask_rate_and_reproducibility():
    m1 = lb.label_mask(100_000, 0.2, seed=7)
    m2 = lb.label_mask(100_000, 0.2, seed=7)
    assert np.array_equal(m1, m2)
    assert abs(m1.mean() - 0.2) < 0.01
    assert lb.label_mask(1000, 1.0, seed=1).all()
    assert not lb.label_mask(1000, 0.0, seed=1).any()


def test_random_mask_ignores_class():
    rng = np.random.default_rng(0)
    y_pred = (rng.random(200_000) < 0.3).astype(int)
    m = lb.label_mask(len(y_pred), 0.5, seed=3)
    assert abs(m[y_pred == 1].mean() - m[y_pred == 0].mean()) < 0.01


def test_alert_first_labels_alerts_more():
    rng = np.random.default_rng(1)
    y_pred = (rng.random(100_000) < 0.2).astype(int)
    m = lb.label_mask(len(y_pred), 0.0, seed=2, mode="alert_first", y_pred=y_pred)
    assert abs(m[y_pred == 1].mean() - 0.9) < 0.01
    assert abs(m[y_pred == 0].mean() - 0.1) < 0.01
    with pytest.raises(ValueError):
        lb.label_mask(10, 0.5, seed=1, mode="alert_first")
    with pytest.raises(ValueError):
        lb.label_mask(10, 0.5, seed=1, mode="other")


def test_cohort_counts_use_labelled_records_only():
    y_true = np.array([1, 1, 0, 0, 1, 0, 0, 0])
    y_pred = np.array([1, 0, 1, 0, 1, 0, 1, 0])
    labelled = np.array([1, 1, 1, 0, 0, 1, 1, 1], dtype=bool)
    c = lb.cohort_counts(y_true, y_pred, labelled, window_size=4)
    assert c[["tp", "fn", "fp", "tn"]].iloc[0].tolist() == [1, 1, 1, 0]
    assert c[["tp", "fn", "fp", "tn"]].iloc[1].tolist() == [0, 0, 1, 2]
    assert c["labelled"].tolist() == [3, 3]


def _counts(attacks_per_window, normals_per_window=1000):
    import pandas as pd

    n = len(attacks_per_window)
    return pd.DataFrame(
        {
            "window": range(n),
            "tp": attacks_per_window,
            "fn": [0] * n,
            "fp": [0] * n,
            "tn": [normals_per_window] * n,
        }
    )


def test_pooling_merges_small_windows_until_eligible():
    rule = lb.PoolingRule(n_min=68, m_min=500, max_span=5)
    cohorts = lb.pool_cohorts(_counts([100, 20, 20, 20, 20, 100]), rule, delay=0)
    assert cohorts["first"].tolist() == [0, 1, 5]
    assert cohorts["last"].tolist() == [0, 4, 5]
    assert cohorts["eligible"].tolist() == [True, True, True]
    assert cohorts["attacks"].tolist() == [100, 80, 100]


def test_pooling_stops_at_max_span_and_marks_ineligible():
    rule = lb.PoolingRule(n_min=68, m_min=500, max_span=5)
    cohorts = lb.pool_cohorts(_counts([5] * 7), rule, delay=0)
    assert cohorts["span"].tolist() == [5, 2]
    assert not cohorts["eligible"].any()


def test_release_time_respects_delay():
    rule = lb.PoolingRule(n_min=10, m_min=10)
    cohorts = lb.pool_cohorts(_counts([50, 50, 50]), rule, delay=5)
    assert cohorts["available_at"].tolist() == [5, 6, 7]
    assert len(lb.released_by(cohorts, 5)) == 1
    assert len(lb.released_by(cohorts, 4)) == 0
    with pytest.raises(ValueError):
        lb.pool_cohorts(_counts([50]), rule, delay=-1)


def test_ipw_cohorts_recover_true_rates():
    rng = np.random.default_rng(4)
    n = 400_000
    y = (rng.random(n) < 0.2).astype(int)
    p = np.where(y == 1, rng.random(n) < 0.9, rng.random(n) < 0.01).astype(int)
    mask = lb.label_mask(n, 0.0, seed=5, mode="alert_first", y_pred=p)
    c = lb.cohort_counts(y, p, mask, window_size=n)
    raw_fpr = c.fp[0] / (c.fp[0] + c.tn[0])
    w = lb.ipw_cohorts(c, lb.P_ALERT, lb.P_NORMAL)
    fpr = w.fp[0] / (w.fp[0] + w.tn[0])
    recall = w.tp[0] / (w.tp[0] + w.fn[0])
    assert raw_fpr > 0.05  # biased upwards
    assert abs(fpr - 0.01) < 0.002
    assert abs(recall - 0.9) < 0.01


def test_kish_ess():
    assert lb.kish_ess(100, 1.0, 0, 10.0) == 100
    assert lb.kish_ess(50, 2.0, 50, 2.0) == pytest.approx(100)
    # 40 heavily weighted records dominate: ESS close to 40, not to the weighted total
    assert lb.kish_ess(20, 1 / 0.9, 40, 100.0) == pytest.approx(40.4, abs=0.5)
    assert lb.kish_ess(0, 1.0, 0, 1.0) == 0.0


def test_pooling_with_weights_uses_effective_size():
    import pandas as pd

    counts = pd.DataFrame(
        {"window": [0, 1], "tp": [900, 900], "fn": [2, 2], "fp": [20, 20], "tn": [40, 40]}
    )
    rule = lb.PoolingRule(n_min=68, m_min=500, max_span=5)
    raw = lb.pool_cohorts(counts, rule, delay=0)
    ess = lb.pool_cohorts(counts, rule, delay=0, weights=(1 / 0.9, 100.0))
    assert not raw["eligible"].any()  # 60 raw normals per window
    assert not ess["eligible"].any()
    weighted = lb.ipw_cohorts(counts, 0.9, 0.01)
    eff = lb.pool_cohorts(weighted, rule, delay=0)
    assert eff["eligible"].all()  # weighted counts look large
    assert isinstance(eff["tn"].iloc[0], float)
