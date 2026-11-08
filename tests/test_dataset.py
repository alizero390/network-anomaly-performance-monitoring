import numpy as np
import pandas as pd
import pytest

from nadmon import dataset


def test_column_layout_has_49_columns():
    assert len(dataset.COLUMN_NAMES) == 49
    assert dataset.feature_name(dataset.STIME_INDEX) == "Stime"
    assert dataset.feature_name(dataset.LABEL_INDEX) == "Label"
    assert dataset.feature_name(dataset.DSPORT_INDEX) == "dsport"


def test_feature_selection_matches_research_decisions():
    numeric = [dataset.feature_name(i) for i in dataset.NUMERIC_FEATURES]
    categorical = [dataset.feature_name(i) for i in dataset.CATEGORICAL_FEATURES]
    assert numeric == [
        "sport", "dsport", "dur", "sbytes", "dbytes", "sttl", "dttl", "sloss",
        "dloss", "Sload", "Dload", "Spkts", "Dpkts", "swin", "dwin",
        "trans_depth", "res_bdy_len", "Sjit", "Djit", "Sintpkt", "Dintpkt",
        "synack", "ackdat",
    ]  # fmt: skip
    assert categorical == ["proto", "state", "service"]


def test_excluded_features_are_not_model_inputs():
    used = {dataset.feature_name(i) for i in dataset.FEATURE_INDICES}
    excluded = {"srcip", "dstip", "attack_cat", "Label", "Stime", "Ltime", "tcprtt",
                "ct_state_ttl", "stcpb", "dtcpb", "is_sm_ips_ports"}  # fmt: skip
    assert used.isdisjoint(excluded)


def test_split_sizes_are_frozen():
    assert dataset.TRAIN_END == 726_426
    assert dataset.VALIDATION_END - dataset.TRAIN_END == 290_575
    assert dataset.FEB_TOTAL - dataset.VALIDATION_END == 435_843


def test_convert_ports_handles_decimal_and_hex():
    raw = pd.Series(["80", " 443 ", "0xcc09", "0XCC09", "52233"], dtype=object)
    converted = dataset.convert_ports(raw)
    assert converted.tolist() == [80, 443, 52233, 52233, 52233]


def test_convert_ports_marks_invalid_values_missing():
    converted = dataset.convert_ports(pd.Series(["-", "0xZZ", "21"], dtype=object))
    assert converted.isna().tolist() == [True, True, False]


def _raw_frame(rows: int = 4) -> pd.DataFrame:
    frame = {i: np.arange(rows) for i in dataset.REQUIRED_COLUMNS}
    frame[dataset.DSPORT_INDEX] = ["80", "0x50", "53", "443"][:rows]
    for i in dataset.CATEGORICAL_FEATURES:
        frame[i] = [" tcp", "udp ", "tcp", "-"][:rows]
    frame[dataset.LABEL_INDEX] = [0, 1, 0, 1][:rows]
    return pd.DataFrame(frame)


def test_preprocess_names_columns_by_original_index():
    X, y = dataset.preprocess(_raw_frame())
    assert list(X.columns) == [str(i) for i in dataset.FEATURE_INDICES]
    assert X["3"].tolist() == [80, 80, 53, 443]
    assert X["4"].tolist() == ["tcp", "udp", "tcp", "-"]
    assert y.tolist() == [0, 1, 0, 1]


def test_preprocess_rejects_invalid_numeric_values():
    raw = _raw_frame()
    raw[dataset.DSPORT_INDEX] = ["80", "bad", "53", "443"]
    with pytest.raises(RuntimeError, match=r"dsport \(column 3\): 1 rows; 'bad' x1"):
        dataset.preprocess(raw)


def test_preprocess_rejects_unexpected_labels():
    raw = _raw_frame()
    raw[dataset.LABEL_INDEX] = [0, 2, 0, 1]
    with pytest.raises(RuntimeError, match="label"):
        dataset.preprocess(raw)


def test_cutoff_must_not_split_timestamp_group(monkeypatch):
    monkeypatch.setattr(dataset, "FEB_TOTAL", 6)
    monkeypatch.setattr(dataset, "VALIDATION_END", 4)
    assert dataset.find_validation_cutoff(np.array([1, 1, 2, 3, 5, 5])) == 3
    with pytest.raises(RuntimeError, match="splits a timestamp group"):
        dataset.find_validation_cutoff(np.array([1, 2, 3, 4, 4, 5]))
