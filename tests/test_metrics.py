import numpy as np
import pandas as pd
import pytest

from nadmon.config import PROJECT_DIR
from nadmon.dataset import WINDOW_SIZE
from nadmon.metrics import binary_metrics, false_positive_rate, window_metrics

RESULTS = PROJECT_DIR / "results"


def test_binary_metrics_known_example():
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_pred = np.array([0, 1, 0, 1, 1, 0])
    m = binary_metrics(y_true, y_pred)
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (2, 1, 1, 2)
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["recall"] == pytest.approx(2 / 3)
    assert m["false_positive_rate"] == pytest.approx(1 / 3)


def test_false_positive_rate_without_negatives_is_zero():
    assert false_positive_rate(fp=0, tn=0) == 0.0


def test_window_metrics_drops_incomplete_tail():
    y = np.array([0, 1] * 6)
    frame = window_metrics(y, y, np.arange(12) + 1_424_242_135, window_size=5)
    assert frame["Window"].tolist() == [1, 2]
    assert frame["F1"].tolist() == [1.0, 1.0]


def test_window_without_attacks_scores_f1_zero():
    # Documents a property the monitoring design must handle explicitly:
    # a window with no attacks gets F1 = 0 even if every prediction is right.
    y = np.zeros(5, dtype=int)
    frame = window_metrics(y, y, np.arange(5), window_size=5)
    assert frame.loc[0, "F1"] == 0.0


@pytest.mark.skipif(
    not (RESULTS / "validation_predictions.csv").is_file(),
    reason="validation_predictions.csv not present (generated, not committed)",
)
def test_window_metrics_reproduce_committed_results():
    predictions = pd.read_csv(RESULTS / "validation_predictions.csv")
    expected = pd.read_csv(RESULTS / "validation_window_metrics.csv")
    actual = window_metrics(
        predictions["TrueLabel"].to_numpy(),
        predictions["Prediction"].to_numpy(),
        predictions["Timestamp"].to_numpy(),
        WINDOW_SIZE,
    )
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
