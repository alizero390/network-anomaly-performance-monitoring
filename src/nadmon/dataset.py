"""UNSW-NB15 loading, February chronological split and feature preprocessing.

The raw CSV files have no header and 49 columns. Model columns are named by
their original column index as strings ("1", "3", ...). The saved baseline
pipeline depends on these names, so they must not change.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

# Original 49-column layout (index -> name).
COLUMN_NAMES: tuple[str, ...] = (
    "srcip", "sport", "dstip", "dsport", "proto", "state", "dur", "sbytes",
    "dbytes", "sttl", "dttl", "sloss", "dloss", "service", "Sload", "Dload",
    "Spkts", "Dpkts", "swin", "dwin", "stcpb", "dtcpb", "smeansz", "dmeansz",
    "trans_depth", "res_bdy_len", "Sjit", "Djit", "Stime", "Ltime", "Sintpkt",
    "Dintpkt", "tcprtt", "synack", "ackdat", "is_sm_ips_ports", "ct_state_ttl",
    "ct_flw_http_mthd", "is_ftp_login", "ct_ftp_cmd", "ct_srv_src",
    "ct_srv_dst", "ct_dst_ltm", "ct_src_ltm", "ct_src_dport_ltm",
    "ct_dst_sport_ltm", "ct_dst_src_ltm", "attack_cat", "Label",
)  # fmt: skip

STIME_INDEX = 28
ATTACK_CAT_INDEX = 47
LABEL_INDEX = 48
DSPORT_INDEX = 3

NUMERIC_FEATURES: tuple[int, ...] = (
    1, 3, 6, 7, 8, 9, 10, 11, 12,
    14, 15, 16, 17, 18, 19, 24, 25,
    26, 27, 30, 31, 33, 34,
)  # fmt: skip
CATEGORICAL_FEATURES: tuple[int, ...] = (4, 5, 13)
FEATURE_INDICES: tuple[int, ...] = NUMERIC_FEATURES + CATEGORICAL_FEATURES
REQUIRED_COLUMNS: list[int] = sorted(FEATURE_INDICES + (STIME_INDEX, LABEL_INDEX))

# February 18, 2015 capture session (UTC epoch seconds, end exclusive).
FEB_START = 1424217600
FEB_END = 1424304000

# Frozen chronological split of the February session.
FEB_TOTAL = 1_452_844
TRAIN_END = 726_426
VALIDATION_END = 1_017_001

WINDOW_SIZE = 5000


def feature_name(index: int) -> str:
    return COLUMN_NAMES[index]


def model_column(index: int) -> str:
    """Column name used inside the model pipeline."""
    return str(index)


def read_february_timestamps(files: Sequence[Path]) -> np.ndarray:
    parts = []
    for file in files:
        print("Reading timestamps:", file.name)
        for chunk in pd.read_csv(
            file,
            header=None,
            usecols=[STIME_INDEX],
            dtype={STIME_INDEX: "int64"},
            chunksize=200_000,
        ):
            stime = chunk[STIME_INDEX]
            selected = stime[(stime >= FEB_START) & (stime < FEB_END)]
            if not selected.empty:
                parts.append(selected.to_numpy(dtype=np.int64))
    return np.concatenate(parts)


def find_validation_cutoff(timestamps: np.ndarray) -> int:
    """Last timestamp of the validation partition.

    Raises if the boundary would split records that share a timestamp.
    """
    if len(timestamps) != FEB_TOTAL:
        raise RuntimeError("February record count does not match the audited total.")

    ordered = np.sort(timestamps, kind="stable")
    cutoff = int(ordered[VALIDATION_END - 1])

    if int(np.count_nonzero(timestamps <= cutoff)) != VALIDATION_END:
        raise RuntimeError(
            "The cutoff timestamp splits a timestamp group. "
            "Do not proceed without resolving the split."
        )
    return cutoff


def load_train_validation(
    files: Sequence[Path],
    cutoff: int,
    extra_columns: Sequence[int] = (),
) -> pd.DataFrame:
    """Load February records up to the cutoff, in stable chronological order.

    ``extra_columns`` adds raw columns (for example attack_cat) without
    changing which rows are loaded or their order.
    """
    columns = sorted(set(REQUIRED_COLUMNS) | set(extra_columns))
    parts = []
    for file in files:
        print("Reading features:", file.name)
        for chunk in pd.read_csv(
            file,
            header=None,
            usecols=columns,
            chunksize=100_000,
            low_memory=False,
        ):
            stime = chunk[STIME_INDEX]
            selected = chunk[(stime >= FEB_START) & (stime <= cutoff)]
            if not selected.empty:
                parts.append(selected)

    data = pd.concat(parts, ignore_index=True)

    if len(data) != VALIDATION_END:
        raise RuntimeError("Loaded record count does not match frozen training/validation split.")

    # Stable sort preserves original file/row order for tied timestamps.
    data = data.sort_values(by=STIME_INDEX, kind="stable").reset_index(drop=True)

    if not data[STIME_INDEX].is_monotonic_increasing:
        raise RuntimeError("Chronological ordering verification failed.")

    return data


def normalize_attack_category(values: pd.Series) -> pd.Series:
    """Clean attack_cat: strip spaces, label blanks as Normal, merge spelling variants."""
    text = values.astype("string").str.strip().fillna("")
    text = text.mask(text == "", "Normal")
    return text.replace({"Backdoors": "Backdoor"}).astype(str)


def convert_ports(values: pd.Series) -> pd.Series:
    """Convert decimal and hexadecimal ("0xcc09") port strings to numbers."""
    text = values.astype("string").str.strip()
    hex_mask = text.str.fullmatch(r"0[xX][0-9a-fA-F]+").fillna(False).astype(bool)

    converted = pd.to_numeric(text.where(~hex_mask), errors="coerce").astype("float64")
    if hex_mask.any():
        converted.loc[hex_mask] = text.loc[hex_mask].map(lambda v: int(v, 16))
    return converted


def preprocess(data: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Convert raw columns to model inputs. Returns (X, y)."""
    data = data.copy()

    data[DSPORT_INDEX] = convert_ports(data[DSPORT_INDEX])

    for index in NUMERIC_FEATURES:
        if index != DSPORT_INDEX:
            data[index] = pd.to_numeric(data[index], errors="coerce")

    for index in CATEGORICAL_FEATURES:
        data[index] = data[index].astype("string").str.strip().astype(str)

    if data[list(FEATURE_INDICES)].isna().any().any():
        raise RuntimeError("Missing or invalid values appeared after conversion.")

    labels = data[LABEL_INDEX].to_numpy(dtype=np.int8)
    if not np.isin(labels, [0, 1]).all():
        raise RuntimeError("Unexpected target label values.")

    X = data[list(FEATURE_INDICES)].copy()
    X.columns = [model_column(i) for i in FEATURE_INDICES]
    return X, labels
