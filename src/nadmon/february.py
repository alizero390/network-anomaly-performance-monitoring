"""February UNSW-NB15 partitions for the strategy experiment (validation and test).

Builds an :class:`nadmon.experiment.Partition` from the raw files: model features,
labels, attack categories and strata (attack category; benign ``service|proto|state``).
Predictions are passed in, so the same code serves the validation run (predictions from
``scripts/baseline.py``) and the one-time test run (predictions from the saved model).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from nadmon import dataset
from nadmon import experiment as ex
from nadmon import scenarios as sc


def load_frames(paths, which: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """(X, y, attack category) for ``which`` = "validation" or "test", in time order."""
    paths.check_raw_files()
    timestamps = dataset.read_february_timestamps(paths.raw_files)
    cutoff = dataset.find_validation_cutoff(timestamps)
    extra = [dataset.ATTACK_CAT_INDEX]
    if which == "validation":
        data = dataset.load_train_validation(paths.raw_files, cutoff, extra_columns=extra)
        data = data.iloc[dataset.TRAIN_END :].reset_index(drop=True)
    elif which == "test":
        data = dataset.load_test(paths.raw_files, cutoff, extra_columns=extra)
    else:
        raise ValueError("which must be 'validation' or 'test'")
    X, y = dataset.preprocess(data)
    category = dataset.normalize_attack_category(data[dataset.ATTACK_CAT_INDEX]).to_numpy()
    return X.reset_index(drop=True), y, category


def partition(X: pd.DataFrame, y: np.ndarray, category: np.ndarray, predictions) -> ex.Partition:
    """Partition with strata and Strategy A feature lists."""
    predictions = np.asarray(predictions, dtype=int)
    if len(predictions) != len(y):
        raise ValueError("predictions and labels differ in length")
    col = dataset.model_column
    strata = sc.unsw_strata(
        y,
        category,
        X[col(dataset.COLUMN_NAMES.index("service"))],
        X[col(dataset.COLUMN_NAMES.index("proto"))],
        X[col(dataset.COLUMN_NAMES.index("state"))],
    )
    return ex.Partition(
        np.asarray(y, dtype=int),
        predictions,
        strata,
        X,
        tuple(col(i) for i in dataset.NUMERIC_FEATURES),
        tuple(col(i) for i in dataset.CATEGORICAL_FEATURES),
    )
