import numpy as np
import pandas as pd
import pytest

from nadmon import evaluation as ev
from nadmon import experiment as ex
from nadmon import scenarios as sc


def _partition(seed=0):
    """Synthetic partition: strata with known rates and stratum-specific features."""
    rng = np.random.default_rng(seed)
    spec = {
        "A:generic": (6000, True, 0.99, 3.0, "udp"),
        "A:exploits": (2000, True, 0.97, 2.5, "tcp"),
        "A:fuzzers": (2000, True, 0.55, 1.0, "tcp"),
        "B:dns": (20000, False, 0.004, 0.0, "udp"),
        "B:http": (15000, False, 0.006, 0.3, "tcp"),
        "B:smtp": (4000, False, 0.005, 0.2, "tcp"),
        "B:noisy": (1000, False, 0.20, -1.0, "udp"),
    }
    strata, y, p, x1, proto = [], [], [], [], []
    for name, (n, attack, rate, mu, pr) in spec.items():
        strata += [name] * n
        y += [int(attack)] * n
        p += list((rng.random(n) < rate).astype(int))
        x1 += list(rng.normal(mu, 1, n))
        proto += [pr] * n
    feats = pd.DataFrame({"x1": x1, "x2": rng.exponential(1, len(y)), "proto": proto})
    return ex.Partition(np.array(y), np.array(p), np.array(strata), feats, ("x1", "x2"), ("proto",))


SMALL = ex.Settings(
    window_size=2000,
    n_windows=20,
    onset=8,
    n_streams=8,
    n_calibration=8,
    delays=(0, 2),
    availabilities=(1.0, 0.5),
    alert_first_delay=2,
    a_reference_size=5000,
)


@pytest.fixture(scope="module")
def run():
    part = _partition()
    ref_idx, pool_idx = ex.split_validation(len(part.y), SMALL.seed)
    ref = ex.a_reference(part.subset(ref_idx), SMALL)
    pool = part.subset(pool_idx)
    cal = ex.base_calibration(part)
    rates = sc.stratum_rates(pool.strata, pool.y, pool.p)
    table = sc.scenario_table(sc.standard_scenarios(rates, cal.pi0), rates, cal.pi0)
    scenarios = [
        x
        for x in sc.standard_scenarios(rates, cal.pi0)
        if table.set_index("scenario").loc[x.name, "usable"]
    ]
    cal = ex.calibrate(pool, scenarios, cal, SMALL, ref, progress=False, natural=part)
    results = ex.run_grid(pool, scenarios, cal, SMALL, ref, progress=False)
    return cal, results


def test_label_conditions():
    names = [c.name for c in ex.label_conditions(ex.Settings())]
    assert len(names) == 10
    assert "d10_p20" in names and "d5_alert_first" in names


def test_split_validation_halves():
    a, b = ex.split_validation(11, seed=1)
    assert len(a) + len(b) == 11 and not set(a) & set(b)


def test_calibration_values(run):
    cal, _ = run
    assert 0 < cal.q <= 1
    assert set(cal.periods) == {0, 2}
    assert cal.n_min > 1


def test_grid_has_every_strategy_and_condition(run):
    _, results = run
    assert set(results["strategy"]) == set(ex.STRATEGIES)
    b = results[results["strategy"] == "B"]
    assert set(b["condition"]) == {c.name for c in ex.label_conditions(SMALL)}
    n_scen = results["scenario"].nunique()
    assert len(b) == n_scen * SMALL.n_streams * len(ex.label_conditions(SMALL))


def test_expected_behaviour_with_random_labels(run):
    _, results = run
    random = results[~results["condition"].str.contains("alert_first")]
    s = ev.summarise(random, ["scenario", "strategy"]).set_index(["scenario", "strategy"])
    # Harmful shifts are detected by B; A warns on input shifts.
    assert s.loc[("X1_hard_attack_mix", "B"), "event_recall"] >= 0.8
    assert s.loc[("X2_false_positive_burst", "B"), "event_recall"] >= 0.8
    assert s.loc[("H1_fewer_attacks", "A"), "false_alert_rate"] >= 0.8
    # Plain F1 alarms on fewer attacks; calibrated F1 does not.
    assert s.loc[("H1_fewer_attacks", "B_F1"), "false_alert_rate"] >= 0.5
    assert s.loc[("H1_fewer_attacks", "B"), "false_alert_rate"] <= 0.1
    assert s.loc[("S0_stable", "B"), "false_alert_rate"] <= 0.1


def test_alert_first_labels_inflate_fpr_and_cause_false_alarms(run):
    """Alert-first labelling over-samples false positives among labelled normals."""
    _, results = run
    af = results[results["condition"].str.contains("alert_first")]
    s = ev.summarise(af, ["scenario", "strategy"]).set_index(["scenario", "strategy"])
    assert s.loc[("S0_stable", "B"), "false_alert_rate"] >= 0.8
    # The weighted variant removes the bias.
    assert s.loc[("S0_stable", "B_ipw"), "false_alert_rate"] <= 0.1
    assert s.loc[("X1_hard_attack_mix", "B_ipw"), "event_recall"] >= 0.8


def test_paired_comparison_runs(run):
    _, results = run
    cmp = ev.paired_comparison(results, "C_active", "B")
    assert len(cmp) > 0
    assert cmp["streams"].min() == SMALL.n_streams


def test_scoring_and_stats():
    s = ev.score_events([3, 8], [5, 10], onset=6, harmful=True)
    assert s["detected"] and s["detection_delay"] == 4 and s["false_alerts"] == 1
    s = ev.score_events([8], [8], onset=6, harmful=False)
    assert not s["detected"] and s["false_alerts"] == 1
    p, lo, hi = ev.wilson(0, 50)
    assert p == 0 and lo == 0 and 0 < hi < 0.1
    assert ev.mcnemar_p([True] * 10, [False] * 10) < 0.01
    assert ev.mcnemar_p([True, False], [True, False]) == 1.0


def test_harder_variants_keep_ground_truth():
    part = _partition()
    rates = sc.stratum_rates(part.strata, part.y, part.p)
    pi0 = float(part.y.mean())
    base = sc.standard_scenarios(rates, pi0)
    variants = sc.harder_variants(base)
    names = {v.name for v in variants}
    assert {"X1_hard_attack_mix_rare", "X1_hard_attack_mix_gradual"} <= names
    table = sc.scenario_table(variants, rates, pi0)
    assert table["usable"].all()
    rare = next(v for v in variants if v.name == "X1_hard_attack_mix_rare")
    assert rare.after.attack_share == 0.02
    gradual = next(v for v in variants if v.name == "X1_hard_attack_mix_gradual")
    comps = sc.window_compositions(gradual, n_windows=20, onset=5)
    shares = [sum(c.attack_mix.get("A:fuzzers", 0) for _ in [0]) for c in comps]
    assert shares[5] < shares[10] < shares[14] == shares[19]


def test_run_natural_reports_every_strategy(run):
    cal, _ = run
    part = _partition()
    ref_idx, _ = ex.split_validation(len(part.y), SMALL.seed)
    ref = ex.a_reference(part.subset(ref_idx), SMALL)
    nat = ex.run_natural(part, cal, SMALL, ref)
    assert set(nat["strategy"]) == {
        "A",
        "A_natural",
        "B_F1",
        "B",
        "B_ipw",
        "C_active",
        "C_active_natural",
    }
    assert (nat["windows"] == len(part.y) // SMALL.window_size).all()


def test_b_ipw_equals_b_under_random_labels(run):
    _, results = run
    random = results[~results["condition"].str.contains("alert_first")]
    b = random[random["strategy"] == "B"].set_index(["scenario", "stream", "condition"])
    w = random[random["strategy"] == "B_ipw"].set_index(["scenario", "stream", "condition"])
    assert (b["alarms"] == w["alarms"]).all()


def test_a_natural_is_quieter(run):
    cal, results = run
    assert cal.q_natural >= cal.q
    s = ev.summarise(results, ["scenario", "strategy"]).set_index(["scenario", "strategy"])
    assert (
        s.loc[("H1_fewer_attacks", "A_natural"), "false_alert_rate"]
        <= s.loc[("H1_fewer_attacks", "A"), "false_alert_rate"]
    )
