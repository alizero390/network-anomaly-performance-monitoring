import numpy as np
import pandas as pd
import pytest

from nadmon import scenarios as sc


def _synthetic(seed=0):
    """Strata with known rates: two easy attack types, one hard; benign services with
    low FPR and one noisy service."""
    rng = np.random.default_rng(seed)
    spec = {
        # stratum: (records, is_attack, rate)
        "A:generic": (6000, True, 0.99),
        "A:exploits": (2000, True, 0.97),
        "A:fuzzers": (2000, True, 0.55),
        "B:dns": (20000, False, 0.004),
        "B:http": (15000, False, 0.006),
        "B:smtp": (4000, False, 0.005),
        "B:noisy": (1000, False, 0.20),
    }
    strata, y, p = [], [], []
    for name, (n, attack, rate) in spec.items():
        strata += [name] * n
        y += [int(attack)] * n
        p += list((rng.random(n) < rate).astype(int))
    return np.array(strata), np.array(y), np.array(p)


@pytest.fixture(scope="module")
def data():
    strata, y, p = _synthetic()
    rates = sc.stratum_rates(strata, y, p)
    return strata, y, p, rates


def test_stratum_rates(data):
    strata, y, p, rates = data
    assert rates.loc["A:fuzzers", "attack"]
    assert not rates.loc["B:dns", "attack"]
    assert abs(rates.loc["A:fuzzers", "rate"] - 0.55) < 0.03
    with pytest.raises(ValueError):
        sc.stratum_rates(np.array(["x", "x"]), np.array([0, 1]), np.array([0, 1]))


def test_base_composition_matches_partition(data):
    strata, y, p, rates = data
    base = sc.base_composition(rates)
    assert base.attack_share == pytest.approx(y.mean())
    assert sum(base.attack_mix.values()) == pytest.approx(1)
    recall, fpr = sc.expected_rates(base, rates)
    assert recall == pytest.approx(p[y == 1].mean())
    assert fpr == pytest.approx(p[y == 0].mean())


def test_shift_mix_moves_weight_to_targets():
    mix = {"a": 0.5, "b": 0.3, "c": 0.2}
    full = sc.shift_mix(mix, ["b", "c"], 1.0)
    assert full.get("a", 0) == 0
    assert full["b"] == pytest.approx(0.6)
    half = sc.shift_mix(mix, ["a"], 0.5)
    assert half["a"] == pytest.approx(0.75)
    with pytest.raises(ValueError):
        sc.shift_mix(mix, ["zz"], 0.5)


def test_standard_scenarios_have_clean_ground_truth(data):
    strata, y, p, rates = data
    pi0 = float(y.mean())
    table = sc.scenario_table(sc.standard_scenarios(rates, pi0), rates, pi0)
    assert set(table["scenario"]) == {
        "S0_stable",
        "H1_fewer_attacks",
        "H2_benign_mix",
        "H3_easy_attack_mix",
        "X1_hard_attack_mix",
        "X2_false_positive_burst",
    }
    assert table["usable"].all(), table[["scenario", "intended", "label"]]
    h1 = table.set_index("scenario").loc["H1_fewer_attacks"]
    assert abs(h1["cal_f1_change"]) < 1e-9  # calibrated F1 ignores the attack share


def test_window_compositions_onset_and_ramp(data):
    strata, y, p, rates = data
    s = sc.standard_scenarios(rates, float(y.mean()))[1]  # H1
    comps = sc.window_compositions(s, n_windows=10, onset=4)
    assert comps[3].attack_share == pytest.approx(s.before.attack_share)
    assert comps[4].attack_share == pytest.approx(s.after.attack_share)
    ramped = sc.window_compositions(s, n_windows=10, onset=4, ramp=4)
    shares = [c.attack_share for c in ramped]
    assert shares[3] > shares[4] > shares[5] > shares[6]
    assert shares[7] == pytest.approx(s.after.attack_share)
    with pytest.raises(ValueError):
        sc.window_compositions(s, n_windows=10, onset=0)


def test_build_stream_follows_composition(data):
    strata, y, p, rates = data
    index = sc.stratum_index(strata)
    scen = {s.name: s for s in sc.standard_scenarios(rates, float(y.mean()))}
    rng = np.random.default_rng(5)
    idx = sc.build_stream(
        scen["H1_fewer_attacks"], index, rng, window_size=2000, n_windows=6, onset=3
    )
    assert len(idx) == 6 * 2000
    share = y[idx].reshape(6, 2000).mean(axis=1)
    assert np.allclose(share[:3], scen["H1_fewer_attacks"].before.attack_share, atol=0.002)
    assert np.allclose(share[3:], 0.02, atol=0.002)


def test_harmful_stream_lowers_recall(data):
    strata, y, p, rates = data
    index = sc.stratum_index(strata)
    scen = {s.name: s for s in sc.standard_scenarios(rates, float(y.mean()))}
    rng = np.random.default_rng(6)
    idx = sc.build_stream(
        scen["X1_hard_attack_mix"], index, rng, window_size=5000, n_windows=4, onset=2
    )
    yt, yp = y[idx].reshape(4, 5000), p[idx].reshape(4, 5000)
    recall = [(yp[w][yt[w] == 1]).mean() for w in range(4)]
    assert recall[2] < recall[0] - 0.05
    gt = sc.ground_truth(
        scen["X1_hard_attack_mix"].before, scen["X1_hard_attack_mix"].after, rates, float(y.mean())
    )
    assert abs(np.mean(recall[2:]) - gt["recall_after"]) < 0.03


def test_stream_is_reproducible(data):
    strata, y, p, rates = data
    index = sc.stratum_index(strata)
    s = sc.standard_scenarios(rates, float(y.mean()))[0]
    a = sc.build_stream(s, index, np.random.default_rng(9), window_size=500, n_windows=4, onset=2)
    b = sc.build_stream(s, index, np.random.default_rng(9), window_size=500, n_windows=4, onset=2)
    assert np.array_equal(a, b)
    assert isinstance(sc.scenario_table([s], rates, 0.2), pd.DataFrame)


def test_unsw_strata_names():
    s = sc.unsw_strata(
        np.array([1, 0, 0, 1]),
        np.array(["Fuzzers", "Normal", "Normal", "Generic"]),
        np.array(["http", "-", "dns", "-"]),
    )
    assert s.tolist() == ["A:Fuzzers", "B:none", "B:dns", "A:Generic"]


def test_unsw_strata_fine_benign():
    s = sc.unsw_strata(
        np.array([0, 1]),
        np.array(["Normal", "DoS"]),
        np.array(["-", "http"]),
        np.array(["udp", "tcp"]),
        np.array(["INT", "FIN"]),
    )
    assert s.tolist() == ["B:none|udp|INT", "A:DoS"]


def test_streams_do_not_depend_on_python_hash_seed(tmp_path):
    """Same seed, same stream in every Python process (bug fixed 2026-11-26)."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    code = (
        "import sys, numpy as np\n"
        f"sys.path[:0] = [{str(root / 'src')!r}, {str(root / 'tests')!r}]\n"
        "from nadmon import experiment as ex, scenarios as sc\n"
        "from test_experiment import _partition\n"
        "part = _partition()\n"
        "cal = ex.base_calibration(part)\n"
        "rates = sc.stratum_rates(part.strata, part.y, part.p)\n"
        "base = sc.standard_scenarios(rates, cal.pi0)\n"
        "scen = base + sc.harder_variants(base)\n"
        "index = sc.stratum_index(part.strata)\n"
        "out = [sc.build_stream(x, index, np.random.default_rng(7), 500, 12, 5)[:3000]"
        " for x in scen]\n"
        "print(np.concatenate(out).sum(), np.concatenate(out)[:50].tolist())\n"
    )
    results = set()
    for seed in ("1", "2", "3"):
        env = {**__import__("os").environ, "PYTHONHASHSEED": seed}
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        results.add(r.stdout)
    assert len(results) == 1
