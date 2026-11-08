"""Sessions, model pipelines and an end-to-end run on small synthetic raw files."""

import importlib.util
import json
import sys

import numpy as np
import pandas as pd
import pytest

from nadmon import dataset, sessions
from nadmon.config import PROJECT_DIR, Paths
from nadmon.models import MODELS

# ---------------------------------------------------------------------------
# Split logic
# ---------------------------------------------------------------------------


def test_split_moves_boundaries_to_timestamp_group_end():
    ts = np.array([1, 1, 2, 2, 2, 3, 4, 4, 5, 6])
    split = sessions.split_session(ts, sessions.Session("x", 0, 10))
    # 50% -> position 5 ends inside the "2" group (positions 3-5): already at its end.
    assert split.train_end == 5
    # 70% -> position 7 falls inside the "4" group (positions 7-8): moved to 8.
    assert split.validation_end == 8
    assert split.cutoff == 4


def test_frozen_split_rejects_wrong_total():
    frozen = sessions.Session("f", 0, 10, total=5, train_end=2, validation_end=3)
    with pytest.raises(RuntimeError, match="audited total"):
        sessions.split_session(np.arange(6), frozen)


def test_frozen_split_rejects_boundary_inside_group():
    frozen = sessions.Session("f", 0, 10, total=6, train_end=2, validation_end=4)
    with pytest.raises(RuntimeError, match="splits a timestamp group"):
        sessions.split_session(np.array([1, 2, 2, 3, 4, 5]), frozen)


def test_dataset_total_matches_project_documentation():
    docs = (PROJECT_DIR / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")
    assert f"{sessions.DATASET_TOTAL:,} records in total" in docs


def test_february_session_matches_frozen_constants():
    feb = sessions.FEBRUARY
    assert (feb.total, feb.train_end, feb.validation_end) == (1_452_844, 726_426, 1_017_001)
    assert sessions.JANUARY.end <= feb.start


def test_sessions_must_cover_dataset():
    jan, feb = sessions.JANUARY, sessions.FEBRUARY
    ok = np.array([jan.start, jan.start + 5, feb.start])
    assert sessions.check_sessions_cover_dataset(ok) == {"feb": 1, "jan": 2}
    with pytest.raises(RuntimeError, match="outside both"):
        sessions.check_sessions_cover_dataset(np.append(ok, 1))


# ---------------------------------------------------------------------------
# Synthetic raw data
# ---------------------------------------------------------------------------

CATEGORIES = ["Generic", "Exploits", "Fuzzers", "DoS"]


def _raw_rows(n: int, start: int, rng: np.random.Generator) -> pd.DataFrame:
    frame = pd.DataFrame(rng.integers(0, 1000, size=(n, 49)))
    label = (rng.random(n) < 0.25).astype(int)
    # Attacks have larger byte counts so the task is learnable.
    frame[7] = rng.integers(0, 1000, n) + label * 800
    frame[1] = rng.integers(1, 65535, n).astype(str)
    dsport = rng.integers(1, 65535, n)
    frame[3] = [hex(p) if i % 50 == 0 else str(p) for i, p in enumerate(dsport)]
    frame[4] = rng.choice(["tcp", "udp", "arp"], n)
    frame[5] = rng.choice(["FIN", "CON", "INT"], n)
    frame[13] = rng.choice(["-", "dns", "http"], n)
    frame[dataset.STIME_INDEX] = start + np.sort(rng.integers(0, n // 3, n))  # ties
    frame[dataset.ATTACK_CAT_INDEX] = np.where(label == 1, rng.choice(CATEGORIES, n), "")
    frame[dataset.LABEL_INDEX] = label
    return frame


@pytest.fixture
def synthetic_dataset(tmp_path, monkeypatch):
    rng = np.random.default_rng(0)
    jan = _raw_rows(3000, sessions.JANUARY.start, rng)
    feb = _raw_rows(2000, sessions.FEBRUARY.start, rng)
    rows = pd.concat([jan, feb], ignore_index=True).sample(frac=1, random_state=1)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for i, idx in enumerate(np.array_split(np.arange(len(rows)), 4), start=1):
        rows.iloc[idx].to_csv(data_dir / f"UNSW-NB15_{i}.csv", header=False, index=False)

    monkeypatch.setattr(sessions, "DATASET_TOTAL", 5000)
    monkeypatch.setattr(dataset, "WINDOW_SIZE", 100)
    return Paths(data_dir=data_dir, project_dir=tmp_path)


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_DIR / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("model", sorted(MODELS))
def test_train_and_analyze_january_run(synthetic_dataset, monkeypatch, model):
    paths = synthetic_dataset
    train = _load_script("train_model")
    monkeypatch.setattr(train, "load_paths", lambda: paths)
    monkeypatch.setattr(sys, "argv", ["train_model.py", "--session", "jan", "--model", model])
    train.main()

    run_dir = paths.results_dir / "runs" / f"jan_{model}"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["split"]["total"] == 3000
    assert summary["records_per_session"] == {"feb": 2000, "jan": 3000}
    assert summary["label_category_mismatches"] == 0
    assert summary["recall"] > 0.6  # the synthetic task is learnable

    pred = pd.read_csv(run_dir / "validation_predictions.csv")
    assert len(pred) == summary["split"]["validation_end"] - summary["split"]["train_end"]
    assert pred["Timestamp"].is_monotonic_increasing
    assert set(pred.loc[pred["TrueLabel"] == 0, "AttackCategory"]) == {"Normal"}

    analyze = _load_script("analyze_attack_share")
    monkeypatch.setattr(analyze, "RESULTS", paths.results_dir)
    monkeypatch.setattr(analyze, "WINDOW_SIZE", 100)
    monkeypatch.setattr(analyze, "SIM_WINDOWS", 200)
    monkeypatch.setattr(sys, "argv", ["analyze_attack_share.py", "--run", f"jan_{model}"])
    analyze.main()

    result = json.loads((run_dir / "attack_share" / "summary.json").read_text(encoding="utf-8"))
    assert result["observed"]["windows"] == len(pred) // 100
    assert {c["AttackCategory"] for c in result["categories"]["categories"]} == set(CATEGORIES)
    assert (run_dir / "attack_share" / "figures" / "fig5_attack_categories_by_window.png").is_file()


def test_random_forest_matches_baseline_script():
    baseline = _load_script("baseline")
    assert repr(baseline.build_pipeline()) == repr(MODELS["rf"]())


def test_describe_january_session(synthetic_dataset, monkeypatch):
    paths = synthetic_dataset
    describe = _load_script("describe_session")
    monkeypatch.setattr(describe, "load_paths", lambda: paths)
    monkeypatch.setattr(describe, "WINDOW", 100)
    describe.main()

    out = paths.results_dir / "sessions" / "jan"
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["records"] == 3000
    parts = summary["default_split_50_20_30"]
    assert sum(p["records"] for p in parts.values()) == 3000
    assert sum(p["attacks"] for p in parts.values()) == summary["attacks"]
    timeline = pd.read_csv(out / "timeline.csv")
    assert timeline["records"].sum() == 3000
    assert timeline["attacks"].sum() == summary["attacks"]
    assert (out / "timeline.png").is_file()


def test_train_stops_when_validation_has_no_attacks(synthetic_dataset, monkeypatch):
    paths = synthetic_dataset
    train = _load_script("train_model")
    monkeypatch.setattr(train, "load_paths", lambda: paths)
    monkeypatch.setattr(train, "MIN_ATTACKS", 10_000)
    monkeypatch.setattr(sys, "argv", ["train_model.py", "--session", "jan", "--model", "rf"])
    with pytest.raises(RuntimeError, match="cannot be measured"):
        train.main()
