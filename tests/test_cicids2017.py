"""CIC-IDS-2017 loading, undefined window metrics, and an end-to-end synthetic run."""

import importlib.util
import json
import sys

import numpy as np
import pandas as pd
import pytest

from nadmon import attack_share as ash
from nadmon import cicids2017 as cic
from nadmon.config import PROJECT_DIR

HEADER = (
    (PROJECT_DIR / "tests" / "data" / "cicids2017_sample.csv")
    .read_text(encoding="utf-8")
    .splitlines()[0]
    .split(",")
)
DAY_DATES = {
    "monday": "2017-07-03",
    "tuesday": "2017-07-04",
    "wednesday": "2017-07-05",
    "thursday": "2017-07-06",
    "friday": "2017-07-07",
}
DAY_ATTACKS = {
    "monday": [],
    "tuesday": ["FTP-Patator"],
    "wednesday": ["DoS Hulk"],
    "thursday": ["Portscan"],
    "friday": ["Portscan", "DDoS"],
}


def _day_frame(day: str, n: int, rng: np.random.Generator) -> pd.DataFrame:
    frame = pd.DataFrame(rng.integers(0, 500, size=(n, len(HEADER))), columns=HEADER)
    seconds = np.sort(rng.integers(0, 8 * 3600, n))
    stamps = pd.Timestamp(f"{DAY_DATES[day]} 12:00:00") + pd.to_timedelta(seconds, unit="s")
    labels = np.array(["BENIGN"] * n, dtype=object)
    attacks = DAY_ATTACKS[day]
    if attacks:
        # Attacks only in the middle third of the day, as in the real data.
        block = slice(n // 3, 2 * n // 3)
        labels[block] = rng.choice(attacks, block.stop - block.start)
        frame.loc[labels != "BENIGN", "Flow Duration"] += 2000  # learnable signal
        labels[n // 3] = f"{attacks[0]} - Attempted"
    frame["id"] = np.arange(1, n + 1)
    frame["Flow ID"] = "a-b-1-2-6"
    frame["Src IP"], frame["Dst IP"] = "192.168.10.9", "192.168.10.3"
    frame["Protocol"] = rng.choice([6, 17, 0], n)
    frame["Timestamp"] = stamps.strftime("%Y-%m-%d %H:%M:%S.%f")
    frame["Label"] = labels
    frame["Attempted Category"] = np.where(pd.Series(labels).str.endswith("Attempted"), 0, -1)
    frame["Flow Bytes/s"] = frame["Flow Bytes/s"].astype(float)
    if day == "monday":
        frame.loc[5, "Flow Bytes/s"] = np.inf
    return frame.sample(frac=1, random_state=0)  # files are not in time order


@pytest.fixture
def cic_folder(tmp_path):
    rng = np.random.default_rng(3)
    folder = tmp_path / "cic"
    folder.mkdir()
    for day in cic.DAYS:
        _day_frame(day, 1200, rng).to_csv(folder / f"{day}.csv", index=False)
    return folder


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_DIR / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_attack_category_maps_attempted_to_normal():
    raw = pd.Series(["BENIGN", "DDoS", "Botnet - Attempted", " Portscan "])
    assert cic.attack_category(raw).tolist() == ["Normal", "DDoS", "Normal", "Portscan"]


def test_feature_columns_exclude_identifiers():
    categorical, numeric = cic.feature_columns(HEADER)
    assert categorical == ["Protocol"]
    assert {"Src Port", "Dst Port", "Flow Duration"} <= set(numeric)
    assert not set(cic.NOT_FEATURES) & set(numeric)
    assert len(categorical) + len(numeric) == len(HEADER) - len(cic.NOT_FEATURES)


def test_load_days_drops_inf_sorts_and_counts(cic_folder):
    data, report = cic.load_days(cic_folder, cic.TRAIN_DAYS)
    assert report["inf_rows_dropped"] == {"monday": 1, "tuesday": 0, "wednesday": 0, "thursday": 0}
    assert report["attempted_as_benign"]["tuesday"] == 1
    assert data["time"].is_monotonic_increasing
    assert len(data) == 4 * 1200 - 1
    X, y = cic.preprocess(data)
    assert np.isfinite(X.drop(columns="Protocol").to_numpy()).all()
    assert set(np.unique(y)) == {0, 1}


def test_undefined_window_metrics_are_nan():
    m = ash.metrics_from_counts(tp=[0, 0, 5], fp=[3, 0, 1], fn=[0, 0, 1], tn=[97, 100, 93])
    assert np.isnan(m["recall"][:2]).all() and m["recall"][2] == pytest.approx(5 / 6)
    assert m["f1"][0] == 0.0  # no attacks, some false positives
    assert np.isnan(m["f1"][1])  # 0/0
    assert np.isnan(m["balanced_accuracy"][0])
    assert m["attack_share"].tolist() == [0.0, 0.0, 0.06]


@pytest.mark.parametrize("model", ["rf", "hgb"])
def test_cicids2017_train_and_analyze(cic_folder, tmp_path, monkeypatch, model):
    train = _load_script("train_cicids2017")
    results = tmp_path / "results"
    monkeypatch.setattr(train, "load_cicids2017_dir", lambda: cic_folder)
    monkeypatch.setattr(train, "RESULTS", results)
    monkeypatch.setattr(train, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(train, "WINDOW_SIZE", 100)
    monkeypatch.setattr(sys, "argv", ["train_cicids2017.py", "--model", model])
    train.main()

    run_dir = results / "runs" / f"cic_{model}"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["split"]["train_end"] == 4 * 1200 - 1
    assert summary["validation_records"] == 1200
    assert summary["recall"] > 0.6

    analyze = _load_script("analyze_attack_share")
    monkeypatch.setattr(analyze, "RESULTS", results)
    monkeypatch.setattr(analyze, "WINDOW_SIZE", 100)
    monkeypatch.setattr(analyze, "SIM_WINDOWS", 200)
    monkeypatch.setattr(sys, "argv", ["analyze_attack_share.py", "--run", f"cic_{model}"])
    analyze.main()

    out = run_dir / "attack_share"
    windows = pd.read_csv(out / "window_metrics_extended.csv")
    no_attacks = windows["attack_share"] == 0
    assert no_attacks.any() and windows.loc[no_attacks, "recall"].isna().all()
    alarms = pd.read_csv(out / "alarms_on_validation.csv")
    recall_rows = alarms[alarms["metric"] == "recall"]
    assert (recall_rows["eligible_windows"] < recall_rows["monitored_windows"]).all()
    result = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert result["categories"]["easy_share_of_attacks"] is None
    assert not (out / "figures" / "fig5_attack_categories_by_window.png").exists()
