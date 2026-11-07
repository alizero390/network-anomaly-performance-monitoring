"""Export the attack category of every validation record.

Run this on the machine that holds the raw dataset:

    python scripts/export_validation_categories.py

It re-uses the frozen February split, so rows line up one-to-one with
results/validation_predictions.csv. Output: results/validation_categories.csv
(about 8 MB; not committed). Then run scripts/analyze_attack_share.py again.

attack_cat is used only for analysis, never as a model feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from nadmon import dataset
from nadmon.config import load_paths


def main() -> None:
    paths = load_paths()
    paths.check_raw_files()
    paths.ensure_output_dirs()

    timestamps = dataset.read_february_timestamps(paths.raw_files)
    cutoff = dataset.find_validation_cutoff(timestamps)
    data = dataset.load_train_validation(
        paths.raw_files, cutoff, extra_columns=[dataset.ATTACK_CAT_INDEX]
    )

    validation = data.iloc[dataset.TRAIN_END :]
    labels = validation[dataset.LABEL_INDEX].to_numpy(dtype=np.int8)
    category = dataset.normalize_attack_category(validation[dataset.ATTACK_CAT_INDEX])

    inconsistent = ((labels == 0) != (category.to_numpy() == "Normal")).sum()
    print("Records with label/category mismatch:", int(inconsistent))

    out = pd.DataFrame(
        {
            "FebruarySortedIndex": np.arange(dataset.TRAIN_END, dataset.VALIDATION_END),
            "CategoryTimestamp": validation[dataset.STIME_INDEX].to_numpy(),
            "CategoryLabel": labels,
            "AttackCategory": category.to_numpy(),
        }
    )
    path = paths.results_dir / "validation_categories.csv"
    out.to_csv(path, index=False, lineterminator="\n")

    print("\nValidation records by category:")
    print(out["AttackCategory"].value_counts().to_string())
    print("\nSaved:", path)


if __name__ == "__main__":
    main()
