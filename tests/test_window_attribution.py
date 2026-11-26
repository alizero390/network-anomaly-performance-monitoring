from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from nadmon import experiment as ex
from nadmon import scenarios as sc
from nadmon import window_attribution as wa
from test_experiment import SMALL, _partition


@pytest.fixture(scope="module")
def run():
    part = _partition()
    ref_idx, pool_idx = ex.split_validation(len(part.y), SMALL.seed)
    ref = ex.a_reference(part.subset(ref_idx), SMALL)
    pool = part.subset(pool_idx)
    cal = ex.base_calibration(part)
    rates = sc.stratum_rates(pool.strata, pool.y, pool.p)
    table = sc.scenario_table(sc.standard_scenarios(rates, cal.pi0), rates, cal.pi0)
    usable = set(table.loc[table["usable"], "scenario"])
    scenarios = [x for x in sc.standard_scenarios(rates, cal.pi0) if x.name in usable]
    cal = ex.calibrate(pool, scenarios, cal, SMALL, ref, progress=False, natural=part)
    results = ex.run_grid(pool, scenarios, cal, SMALL, ref, progress=False)
    return {"pool": pool, "scenarios": scenarios, "cal": cal, "results": results}


REF = wa.References(pi0=0.2, recall=0.97, fpr=0.005, f1_calibrated=0.97, n_min=68, drop=0.05)


def _window(attacks, missed, normals, fps, cat="Generic", missed_cat=None):
    y = np.r_[np.ones(attacks, int), np.zeros(normals, int)]
    p = np.r_[
        np.zeros(missed, int),
        np.ones(attacks - missed, int),
        np.ones(fps, int),
        np.zeros(normals - fps, int),
    ]
    c = np.array(
        [missed_cat or cat] * missed + [cat] * (attacks - missed) + ["Normal"] * normals,
        dtype=object,
    )
    return y, p, c


def test_causes_follow_rule_order():
    assert wa.cause(50, 0.5, 0.5, REF) == "too_few_attacks"
    assert wa.cause(500, 0.90, 0.5, REF) == "missed_attacks"
    assert wa.cause(500, 0.95, 0.02, REF) == "false_positive_burst"
    assert wa.cause(500, 0.95, 0.005, REF) == "attack_share_effect"
    assert REF.fp_burst == 0.01


def test_window_table_flags_and_names_the_missed_category():
    parts = [
        _window(1000, 20, 4000, 10),  # healthy
        _window(1000, 200, 4000, 10, missed_cat="Fuzzers"),  # missed Fuzzers
        _window(1000, 20, 4000, 200),  # false-positive burst
    ]
    y = np.concatenate([a for a, _, _ in parts])
    p = np.concatenate([b for _, b, _ in parts])
    c = np.concatenate([x for _, _, x in parts])
    windows, cats = wa.window_table(y, p, c, 5000, REF)
    assert windows["window"].tolist() == [1, 2, 3]
    assert windows["flagged"].tolist() == [False, True, True]
    assert windows.loc[1, "cause"] == "missed_attacks"
    assert windows.loc[1, "top_missed_category"] == "Fuzzers"
    assert windows.loc[1, "top_missed_share_of_misses"] == 1.0
    assert windows.loc[2, "cause"] == "false_positive_burst"
    assert abs(windows.loc[0, "recall"] - 0.98) < 1e-12
    w2 = cats[cats["window"] == 2].set_index("category")
    assert w2.loc["Fuzzers", "missed"] == 200 and w2.loc["Fuzzers", "recall"] == 0.0


def test_category_shift_separates_mix_from_recall():
    cats = pd.DataFrame(
        [
            (1, "Generic", 900, 9),
            (1, "Fuzzers", 100, 30),
            (2, "Generic", 500, 5),
            (2, "Fuzzers", 500, 150),  # more Fuzzers, same recall
        ],
        columns=["window", "category", "attacks", "missed"],
    )
    cats["recall"] = 1 - cats["missed"] / cats["attacks"]
    mix = wa.category_shift(cats, [2], [1]).set_index("category")
    assert mix.loc["Fuzzers", "share_change"] == 0.4
    assert abs(mix.loc["Fuzzers", "recall_change"]) < 1e-12
    # all misses explained by the mix: observed equals expected at baseline recall
    assert abs(mix.loc["Fuzzers", "missed_expected_at_baseline_recall"] - 150) < 1e-9


def test_b_alone_reproduces_the_full_grid(run):
    """The sensitivity script runs B without Strategy A; B's rows must not change."""
    pool, scenarios, cal, results = run["pool"], run["scenarios"], run["cal"], run["results"]
    alone = ex.run_grid(pool, scenarios, cal, SMALL, None, progress=False)
    key = ["scenario", "stream", "condition", "strategy"]
    cols = ["detected", "detection_delay", "false_alerts", "alarms"]
    full = results[results["strategy"].isin(["B", "B_F1", "B_ipw"])][key + cols]
    m = alone[key + cols].merge(full, on=key, suffixes=("", "_full"))
    assert len(m) == len(full) > 0
    for c in cols:
        a, b = m[c].to_numpy(float), m[c + "_full"].to_numpy(float)
        assert ((a == b) | (np.isnan(a) & np.isnan(b))).all()


def test_lower_drop_never_alarms_later(run):
    pool, scenarios, cal = run["pool"], run["scenarios"], run["cal"]
    lo = ex.run_grid(pool, scenarios, cal, replace(SMALL, drop=0.03), None, progress=False)
    hi = ex.run_grid(pool, scenarios, cal, replace(SMALL, drop=0.10), None, progress=False)
    key = ["scenario", "stream", "condition", "strategy"]
    m = lo.merge(hi, on=key, suffixes=("_lo", "_hi"))
    assert (m["alarms_lo"] >= 0).all()
    harmful = m[m["harmful_lo"]]
    assert harmful["detected_lo"].sum() >= harmful["detected_hi"].sum()
