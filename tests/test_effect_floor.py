import numpy as np
import pandas as pd
import pytest

from nadmon import effect_floor as ef
from nadmon import experiment as ex
from nadmon import rolling_a as ra
from nadmon import scenarios as sc
from nadmon import strategies as st
from test_experiment import SMALL, _partition
from test_rolling_a import S, W, _stream


def test_total_variation():
    ref = pd.Series({"tcp": 70, "udp": 30})
    assert st.total_variation(ref, pd.Series(["tcp"] * 7 + ["udp"] * 3)) == pytest.approx(0)
    assert st.total_variation(ref, pd.Series(["udp"] * 10)) == pytest.approx(0.7)
    assert st.total_variation(ref, pd.Series(["icmp"] * 10)) == pytest.approx(1.0)


def test_feature_tests_match_pvalues_and_effects():
    part = _stream(n_windows=6, seed=1)
    frames = ra.window_frames(part, np.arange(6 * W), W)
    ref = st.Reference.from_frame(pd.concat(frames[:4]), part.numeric, part.categorical)
    tests = st.window_feature_tests(ref, frames[5])
    p = st.window_feature_pvalues(ref, frames[5])
    assert np.allclose(tests["p"], p[tests.index])
    assert tests["effect"].between(0, 1).all()
    assert tests.loc["x1", "effect"] < 0.1  # same distribution: small KS statistic


def test_floor_zero_equals_d21_and_floor_removes_tiny_changes():
    part = _stream(n_windows=30, shift_at=18, shift=0.08, seed=5)  # small real shift
    idx = np.arange(30 * W)
    tests = ef.rolling_tests(part, idx, S, seed=1)
    plain = ef.proportions(tests, S.a_alpha, 0.0)
    assert np.allclose(plain, ra.rolling_proportions(part, idx, S, seed=1))
    floored = ef.proportions(tests, S.a_alpha, 0.10)
    assert (floored <= plain).all()
    assert floored.max() == 0  # a 0.08-sd shift moves KS by ~0.03 < 0.10


def test_large_change_survives_the_floor():
    part = _stream(n_windows=30, shift_at=18, shift=1.0, seed=6)
    tests = ef.rolling_tests(part, np.arange(30 * W), S, seed=1)
    assert ef.proportions(tests, S.a_alpha, 0.10)[18:21].min() >= 1 / 3


def test_choose_epsilon():
    def t(effects):
        return pd.DataFrame({"p": [1e-9] * len(effects), "effect": effects}, index=["a", "b", "c"])

    tests = [None, t([0.04, 0.0, 0.0]), t([0.06, 0.0, 0.0]), t([0.01, 0.0, 0.0])]
    eps, shares = ef.choose_epsilon(tests, alpha=0.01, q=0.3, grid=(0.02, 0.05, 0.1), target=0.4)
    assert shares[0.02] == pytest.approx(2 / 3)
    assert eps == 0.05 and shares[0.05] == pytest.approx(1 / 3)
    eps, _ = ef.choose_epsilon(tests, alpha=0.01, q=0.3, grid=(0.02,), target=0.0)
    assert eps == 0.02  # none qualifies: largest grid value


@pytest.fixture(scope="module")
def grid():
    part = _partition()
    _, pool_idx = ex.split_validation(len(part.y), SMALL.seed)
    pool = part.subset(pool_idx)
    cal = ex.base_calibration(part)
    rates = sc.stratum_rates(pool.strata, pool.y, pool.p)
    table = sc.scenario_table(sc.standard_scenarios(rates, cal.pi0), rates, cal.pi0)
    usable = set(table.loc[table["usable"], "scenario"])
    scenarios = [x for x in sc.standard_scenarios(rates, cal.pi0) if x.name in usable]
    rolling = ra.RollingCalibration(lookback=3, gap=1, q_rolling=1 / 3, periods={0: 1, 2: 2})
    fc = ef.calibrate(part, pool, scenarios, SMALL, rolling, progress=False)
    res = ef.run_grid(pool, scenarios, cal, fc, SMALL, progress=False)
    return fc, res, part, cal


def test_calibration_and_grid(grid):
    fc, res, _, _ = grid
    assert fc.epsilon in ef.EPSILON_GRID and fc.q is not None
    assert set(fc.real_window_share) == set(ef.EPSILON_GRID)
    assert set(res["strategy"]) == set(ef.STRATEGIES)
    key = ["scenario", "stream", "condition"]
    harm = res[res["harmful"]]
    b = harm[harm["strategy"] == "B"].set_index(key)["detection_delay"]
    c = (
        harm[harm["strategy"] == "C_active_floor"]
        .set_index(key)["detection_delay"]
        .reindex(b.index)
    )
    both = b.notna() & c.notna()
    assert (c[both] <= b[both]).all()


def test_natural(grid):
    fc, _, part, cal = grid
    alarms, windows = ef.run_natural(part, cal, fc, SMALL, seed=1)
    assert alarms.iloc[0]["strategy"] == "A_floor"
    assert (windows["changed_proportion_floor"] <= windows["changed_proportion_no_floor"]).all()
