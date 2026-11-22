import numpy as np
import pandas as pd
import pytest

from nadmon import experiment as ex
from nadmon import rolling_a as ra
from nadmon import scenarios as sc
from nadmon import strategies as st
from test_experiment import SMALL, _partition

W = 1000


def _stream(n_windows=30, shift_at=None, base=0.0, shift=1.0, seed=0):
    """Partition in time order; feature x1 jumps by ``shift`` from window ``shift_at``."""
    rng = np.random.default_rng(seed)
    n = n_windows * W
    mu = np.full(n, base)
    if shift_at is not None:
        mu[shift_at * W :] += shift
    feats = pd.DataFrame(
        {
            "x1": rng.normal(mu, 1),
            "x2": rng.exponential(1, n),
            "proto": rng.choice(["tcp", "udp"], n, p=[0.7, 0.3]),
        }
    )
    return ex.Partition(
        np.zeros(n, dtype=int),
        np.zeros(n, dtype=int),
        np.array(["B:x"] * n),
        feats,
        ("x1", "x2"),
        ("proto",),
    )


S = ex.Settings(window_size=W, a_reference_size=4000)


def test_rolling_windows():
    assert ra.rolling_windows(14) == list(range(0, 10))
    assert ra.rolling_windows(20) == list(range(6, 16))
    assert ra.rolling_windows(13) == []
    assert ra.rolling_windows(3, lookback=2, gap=1) == [1, 2]


def test_rolling_reference_flags_a_jump_then_absorbs_it():
    part = _stream(n_windows=40, shift_at=18)
    props = ra.rolling_proportions(part, np.arange(40 * W), S, seed=1)
    assert (props[:14] == 0).all()  # no full reference yet: not judged
    assert props[14:18].max() < 1 / 3  # stable before the jump
    assert (props[18:23] >= 1 / 3).all()  # reference still before the jump
    assert props[32:].max() < 1 / 3  # reference windows 18+ only: absorbed


def test_fixed_stale_reference_flags_everything_rolling_does_not():
    """The test-run failure: a reference from another period flags every window."""
    stale = _stream(n_windows=5, base=0.0, seed=3)
    ref = st.Reference.from_frame(stale.features, stale.numeric, stale.categorical)
    later = _stream(base=0.3, seed=4)  # one period later, slightly different traffic
    frames = ra.window_frames(later, np.arange(30 * W), W)
    fixed = st.changed_proportion(ref, frames)
    rolling = ra.rolling_proportions(later, np.arange(30 * W), S, seed=2)
    assert (fixed >= 1 / 3).all()
    assert rolling[14:].max() < 1 / 3


def _monitored(rows):
    return pd.DataFrame(rows, columns=["first", "last", "available_at", "eligible_eval", "flagged"])


def test_healthy_windows_need_released_unflagged_eligible_cohorts():
    m = _monitored(
        [
            (0, 2, 5, True, False),
            (3, 4, 7, True, True),  # flagged: not healthy
            (5, 6, 9, False, False),  # not eligible
            (7, 8, 11, True, False),
        ]
    )
    assert ra.healthy_windows(m, 4) == []
    assert ra.healthy_windows(m, 5) == [0, 1, 2]
    assert ra.healthy_windows(m, 11) == [0, 1, 2, 7, 8]


def test_anchored_waits_for_enough_healthy_windows():
    part = _stream(n_windows=12)
    m = _monitored([(w, w, w + 2, True, False) for w in range(12)])
    props = ra.anchored_proportions(part, np.arange(12 * W), S, m, lookback=3, seed=0)
    # window w knows windows released by w, i.e. up to w - 2; three are needed
    assert (props[:4] == 0).all()
    assert props[5:].max() < 1 / 3


@pytest.fixture(scope="module")
def grid():
    part = _partition()
    _, pool_idx = ex.split_validation(len(part.y), SMALL.seed)
    pool = part.subset(pool_idx)
    cal = ex.base_calibration(part)
    rates = sc.stratum_rates(pool.strata, pool.y, pool.p)
    table = sc.scenario_table(sc.standard_scenarios(rates, cal.pi0), rates, cal.pi0)
    scenarios = [
        x
        for x in sc.standard_scenarios(rates, cal.pi0)
        if table.set_index("scenario").loc[x.name, "usable"]
    ]
    conds = ex.label_conditions(SMALL)
    names = tuple(c.name for c in conds)
    old = (ra.ANCHORED_CONDITIONS, ra.ANCHORED_CALIBRATION)
    ra.ANCHORED_CONDITIONS, ra.ANCHORED_CALIBRATION = (names[0],), names[0]
    try:
        rc = ra.calibrate(pool, scenarios, cal, SMALL, progress=False, lookback=3, gap=1)
        new = ra.run_grid(pool, scenarios, cal, rc, SMALL, progress=False)
    finally:
        ra.ANCHORED_CONDITIONS, ra.ANCHORED_CALIBRATION = old
    previous = ex.run_grid(pool, scenarios, cal, SMALL, None, progress=False)
    return rc, new, previous, part, cal


def test_calibration(grid):
    rc = grid[0]
    assert rc.q_rolling is not None and 0 < rc.q_rolling <= 1 + 1e-6
    assert rc.q_anchored is not None
    assert set(rc.periods) == set(SMALL.delays)


def test_grid_reproduces_b_and_has_every_variant(grid):
    _, new, previous, _, _ = grid
    assert set(new["strategy"]) == {"A_rolling", "A_anchored", "B", "C_active_rolling"}
    key = ["scenario", "stream", "condition"]
    cols = ["detected", "detection_delay", "false_alerts", "alarms"]
    a = new[new["strategy"] == "B"].set_index(key)[cols].sort_index()
    b = previous[previous["strategy"] == "B"].set_index(key)[cols].sort_index()
    pd.testing.assert_frame_equal(a, b)


def test_c_active_rolling_is_never_slower_than_b(grid):
    new = grid[1]
    key = ["scenario", "stream", "condition"]
    harm = new[new["harmful"]]
    b = harm[harm["strategy"] == "B"].set_index(key)["detection_delay"]
    c = harm[harm["strategy"] == "C_active_rolling"].set_index(key)["detection_delay"]
    both = b.notna() & c.reindex(b.index).notna()
    assert (c.reindex(b.index)[both] <= b[both]).all()


def test_run_natural(grid):
    rc, _, _, part, cal = grid
    nat = ra.run_natural(part, cal, rc, SMALL, seed=1)
    assert nat.iloc[0]["strategy"] == "A_rolling"
    assert set(nat["strategy"]) == {"A_rolling", "B", "C_active_rolling"}
