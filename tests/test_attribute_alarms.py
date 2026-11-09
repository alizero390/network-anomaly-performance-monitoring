import importlib.util

import numpy as np
import pandas as pd

from nadmon.config import PROJECT_DIR


def _load():
    path = PROJECT_DIR / "scripts" / "attribute_alarms.py"
    spec = importlib.util.spec_from_file_location("attribute_alarms", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_confirmed_windows_skip_ineligible():
    attr = _load()
    values = np.array([0.95, 0.80, np.nan, 0.80, 0.95, 0.80])
    flagged, confirmed = attr.confirmed_windows(values, ref=0.95, start=0)
    assert flagged == [1, 3, 5]
    assert confirmed == [3]  # windows 1 and 3 are consecutive eligible windows


def test_attribution_matches_committed_alarm_tables(tmp_path, monkeypatch):
    attr = _load()
    monkeypatch.setattr(attr, "OUT", tmp_path)
    attr.main()  # raises if any confirmed-alarm count differs from the analysis
    summary = pd.read_csv(tmp_path / "summary.csv")
    assert set(attr.CAUSES) <= set(summary.columns)
    assert (summary["total"] == summary[list(attr.CAUSES)].sum(axis=1)).all()
