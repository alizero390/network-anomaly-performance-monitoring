import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score, matthews_corrcoef

from nadmon import attack_share as ash
from nadmon.dataset import normalize_attack_category


def test_f1_from_rates_matches_counts():
    # 100 attacks, 900 normals, TPR 0.9, FPR 0.01 -> TP 90, FN 10, FP 9.
    assert ash.f1_from_rates(0.9, 0.01, 0.1) == pytest.approx(2 * 90 / (2 * 90 + 9 + 10))


def test_mcc_from_rates_matches_sklearn():
    y = np.array([1] * 100 + [0] * 900)
    pred = np.array([1] * 90 + [0] * 10 + [1] * 9 + [0] * 891)
    assert ash.mcc_from_rates(0.9, 0.01, 0.1) == pytest.approx(matthews_corrcoef(y, pred))


def test_f1_falls_with_attack_share_at_fixed_rates():
    shares = np.array([0.01, 0.05, 0.2, 0.5])
    f1 = ash.f1_from_rates(0.97, 0.005, shares)
    assert np.all(np.diff(f1) > 0)


def test_metrics_from_counts_match_sklearn():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 500)
    pred = np.where(rng.random(500) < 0.8, y, 1 - y)
    tp = int(((y == 1) & (pred == 1)).sum())
    fp = int(((y == 0) & (pred == 1)).sum())
    fn = int(((y == 1) & (pred == 0)).sum())
    tn = int(((y == 0) & (pred == 0)).sum())
    m = ash.metrics_from_counts(tp, fp, fn, tn)
    assert float(m["f1"]) == pytest.approx(f1_score(y, pred))
    assert float(m["mcc"]) == pytest.approx(matthews_corrcoef(y, pred))


def test_window_table_counts_and_shares():
    y = np.array([0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0])
    pred = np.array([0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0])
    score = pred * 0.8 + 0.1
    table = ash.window_table(y, pred, score, np.arange(11) + 1_424_242_135, window_size=5)
    assert len(table) == 2
    assert table.loc[0, ["tp", "fp", "fn", "tn"]].tolist() == [1, 1, 1, 2]
    assert table["attack_share"].tolist() == [0.4, 0.8]


def test_decompose_share_only_tracks_formula():
    windows = pd.DataFrame({"attack_share": [0.05, 0.3], "recall": [0.9, 0.99], "fpr": [0.01, 0.0]})
    out = ash.decompose_f1(windows, tpr=0.95, fpr=0.005, share=0.2)
    assert out["f1_share_only"].tolist() == pytest.approx(
        list(ash.f1_from_rates(0.95, 0.005, np.array([0.05, 0.3])))
    )
    assert out.loc[1, "f1_performance_only"] > out.loc[0, "f1_performance_only"]


def test_resampling_keeps_per_class_rates():
    y = np.array([1] * 1000 + [0] * 9000)
    pred = np.concatenate([np.r_[np.ones(900), np.zeros(100)], np.r_[np.ones(90), np.zeros(8910)]])
    sim = ash.resample_at_shares(y, pred, [0.02, 0.4], 2000, 300, seed=0)
    by_share = sim.groupby("target_share")[["recall", "fpr", "attack_share"]].mean()
    assert by_share["recall"].tolist() == pytest.approx([0.9, 0.9], abs=0.01)
    assert by_share["fpr"].tolist() == pytest.approx([0.01, 0.01], abs=0.002)
    assert by_share["attack_share"].tolist() == pytest.approx([0.02, 0.4])


def test_resampling_is_reproducible():
    y = np.array([1, 0] * 500)
    pred = y.copy()
    a = ash.resample_at_shares(y, pred, [0.1], 100, 20, seed=7)
    b = ash.resample_at_shares(y, pred, [0.1], 100, 20, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_alarm_needs_consecutive_windows():
    ref = 0.95
    isolated = np.array([0.95, 0.88, 0.95, 0.88, 0.95, 0.95])  # never two in a row
    paired = np.array([0.95, 0.88, 0.89, 0.95, 0.95, 0.95])
    assert ash.alarm_rate(isolated, ref, 0.05, 2, stream_length=6) == 0.0
    assert ash.alarm_rate(paired, ref, 0.05, 2, stream_length=6) == 1.0


def test_alarm_rate_counts_streams():
    values = np.r_[[0.8, 0.8, 0.95], [0.95, 0.95, 0.95]]
    assert ash.alarm_rate(values, 0.95, 0.05, 2, stream_length=3) == 0.5


def test_normalize_attack_category():
    raw = pd.Series([" Exploits", "", None, "Backdoors", "Generic "], dtype=object)
    assert normalize_attack_category(raw).tolist() == [
        "Exploits",
        "Normal",
        "Normal",
        "Backdoor",
        "Generic",
    ]
