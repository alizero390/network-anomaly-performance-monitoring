"""Improved CIC-IDS-2017 (Engelen et al. 2021; Liu et al. 2022): loading and preprocessing.

Decisions (RESEARCH_DECISIONS.md, section 14, approved 2026-11-09):

- Split: train on Monday-Thursday, monitor Friday. No test set is held out.
- "Attempted" flows (failed attack connections) are labelled BENIGN, as in the
  dataset authors' own benchmark.
- The 8 rows with infinite Flow Bytes/s or Flow Packets/s are dropped; negative
  header lengths are kept as recorded.
- Identifiers (id, Flow ID, Src IP, Dst IP, Timestamp) are not features. Ports are
  kept, as for UNSW-NB15. Protocol is categorical, as UNSW-NB15's proto.
- Rows are sorted by Timestamp (stable) within the training days and within Friday.
  The CSV timestamps carry no time zone; they are used as given.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
TRAIN_DAYS = ("monday", "tuesday", "wednesday", "thursday")
MONITOR_DAY = "friday"

BENIGN = "BENIGN"
NORMAL_CATEGORY = "Normal"  # name used for benign traffic across the project
ATTEMPTED_SUFFIX = " - Attempted"

NOT_FEATURES = ("id", "Flow ID", "Src IP", "Dst IP", "Timestamp", "Label", "Attempted Category")
DERIVED = ("category", "time", "day", "label", "timestamp")  # added by load_days
CATEGORICAL = ("Protocol",)
INF_COLUMNS = ("Flow Bytes/s", "Flow Packets/s")
SKIP_ON_READ = ("id", "Flow ID", "Src IP", "Dst IP")  # identifiers, never used


def feature_columns(columns: Sequence[str]) -> tuple[list[str], list[str]]:
    """(categorical, numeric) model feature columns from a header."""
    excluded = set(NOT_FEATURES) | set(DERIVED) | set(CATEGORICAL)
    numeric = [c for c in columns if c not in excluded]
    return list(CATEGORICAL), numeric


def attack_category(labels: pd.Series) -> pd.Series:
    """Map raw labels to categories; Attempted flows and BENIGN become Normal."""
    text = labels.astype(str).str.strip()
    benign = (text == BENIGN) | text.str.endswith(ATTEMPTED_SUFFIX)
    return text.mask(benign, NORMAL_CATEGORY)


def load_days(folder: Path, days: Sequence[str]) -> tuple[pd.DataFrame, dict]:
    """Load, clean and time-sort the given days. Returns (data, report)."""
    parts, report = [], {"rows_read": {}, "inf_rows_dropped": {}, "attempted_as_benign": {}}
    for day in days:
        path = folder / f"{day}.csv"
        print("Reading", path.name)
        header = pd.read_csv(path, nrows=0).columns
        keep = [c for c in header if c not in SKIP_ON_READ]
        _, numeric = feature_columns(header)
        frame = pd.read_csv(path, usecols=keep, dtype=dict.fromkeys(numeric, "float32"))
        report["rows_read"][day] = int(len(frame))

        inf_rows = np.isinf(frame[list(INF_COLUMNS)].to_numpy(dtype="float64")).any(axis=1)
        report["inf_rows_dropped"][day] = int(inf_rows.sum())
        frame = frame.loc[~inf_rows]

        labels = frame["Label"].astype(str).str.strip()
        report["attempted_as_benign"][day] = int(labels.str.endswith(ATTEMPTED_SUFFIX).sum())
        frame = frame.assign(
            category=attack_category(frame["Label"]),
            time=pd.to_datetime(frame["Timestamp"]),
            day=day,
        )
        parts.append(frame)

    data = pd.concat(parts, ignore_index=True)
    data = data.sort_values("time", kind="stable").reset_index(drop=True)
    data["label"] = (data["category"] != NORMAL_CATEGORY).astype(np.int8)
    # Seconds since the epoch, for the shared window and timeline code.
    # Unit-independent: pandas may store parsed times in us or ns.
    data["timestamp"] = (data["time"] - pd.Timestamp("1970-01-01")) / pd.Timedelta(seconds=1)
    return data, report


def preprocess(data: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Model inputs (X) and binary labels (y)."""
    categorical, numeric = feature_columns(data.columns)
    X = data[categorical + numeric].copy()
    X[numeric] = X[numeric].apply(pd.to_numeric, errors="raise").astype("float32")
    for column in categorical:
        X[column] = X[column].astype(str)
    if not np.isfinite(X[numeric].to_numpy()).all():
        raise RuntimeError("Non-finite feature values remain after cleaning.")
    return X, data["label"].to_numpy()
