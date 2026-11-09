"""Model pipelines. Settings are fixed in advance, not tuned on validation data."""

from __future__ import annotations

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

from nadmon import dataset

RANDOM_STATE = 42

CATEGORICAL = [dataset.model_column(i) for i in dataset.CATEGORICAL_FEATURES]
NUMERIC = [dataset.model_column(i) for i in dataset.NUMERIC_FEATURES]


def random_forest(categorical=None, numeric=None) -> Pipeline:
    """The baseline: identical to scripts/baseline.py (UNSW-NB15 columns by default)."""
    categorical = CATEGORICAL if categorical is None else list(categorical)
    numeric = NUMERIC if numeric is None else list(numeric)
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                categorical,
            ),
            ("numerical", "passthrough", numeric),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


def gradient_boosting(categorical=None, numeric=None) -> Pipeline:
    """Histogram gradient boosting with native categorical handling.

    Unseen categories become missing values, which the model handles natively.
    Early stopping is off so no random internal validation split is drawn.
    """
    categorical = CATEGORICAL if categorical is None else list(categorical)
    numeric = NUMERIC if numeric is None else list(numeric)
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=np.nan,
                    encoded_missing_value=np.nan,
                ),
                categorical,
            ),
            ("numerical", "passthrough", numeric),
        ]
    )
    classifier = HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.1,
        early_stopping=False,
        class_weight="balanced",
        categorical_features=list(range(len(categorical))),
        random_state=RANDOM_STATE,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", classifier)])


MODELS = {"rf": random_forest, "hgb": gradient_boosting}
