"""Profile the improved CIC-IDS-2017 day files before designing the experiment.

Usage:  python scripts/profile_cicids2017.py

Reads monday.csv ... friday.csv from the configured folder (cicids2017_dir in
configs/paths.toml). No model is trained. Writes to results/cicids2017_profile/:
    summary.json          rows, time range, ordering, labels, invalid values per day
    labels_by_day.csv     Label x day counts
    attempted.csv         Label x Attempted Category counts
    attacks_by_hour.csv   attack flows per hour and label (non-attempted)
    invalid_values.csv    NaN / inf / negative counts per numeric column and day
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from nadmon.config import PROJECT_DIR, load_cicids2017_dir
from nadmon.provenance import run_metadata

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
BENIGN = "BENIGN"
ID_COLUMNS = {"id", "Flow ID", "Src IP", "Dst IP", "Timestamp", "Label", "Attempted Category"}
OUT = PROJECT_DIR / "results" / "cicids2017_profile"


def profile_day(path) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    rows = 0
    ids, labels, attempted, stamps = [], [], [], []
    invalid = None
    columns = None
    for chunk in pd.read_csv(path, chunksize=200_000, low_memory=False):
        if columns is None:
            columns = list(chunk.columns)
        rows += len(chunk)
        ids.append(chunk["id"].to_numpy())
        labels.append(chunk["Label"].astype(str).str.strip().to_numpy())
        attempted.append(chunk["Attempted Category"].astype(str).str.strip().to_numpy())
        stamps.append(chunk["Timestamp"].astype(str).to_numpy())

        numeric = chunk.drop(columns=[c for c in chunk.columns if c in ID_COLUMNS])
        numeric = numeric.apply(pd.to_numeric, errors="coerce")
        counts = pd.DataFrame(
            {
                "nan": numeric.isna().sum(),
                "inf": np.isinf(numeric.to_numpy(dtype="float64")).sum(axis=0),
                "negative": (numeric < 0).sum(),
            }
        )
        invalid = counts if invalid is None else invalid + counts

    ids = np.concatenate(ids)
    labels = np.concatenate(labels)
    attempted = np.concatenate(attempted)
    parsed = pd.to_datetime(pd.Series(np.concatenate(stamps)), errors="coerce")

    frame = pd.DataFrame({"time": parsed, "label": labels, "attempted": attempted})
    is_attack = (frame["label"] != BENIGN) & (frame["attempted"] == "-1")
    by_hour = (
        frame[is_attack]
        .groupby([frame["time"].dt.floor("h"), "label"])
        .size()
        .rename("flows")
        .reset_index()
    )
    ordered = parsed.dropna()

    summary = {
        "rows": int(rows),
        "columns": len(columns),
        "duplicate_ids": int(pd.Series(ids).duplicated().sum()),
        "unparsed_timestamps": int(parsed.isna().sum()),
        "time_min": str(ordered.min()),
        "time_max": str(ordered.max()),
        "rows_in_time_order": bool(ordered.is_monotonic_increasing),
        "distinct_timestamps": int(ordered.nunique()),
        "labels": pd.Series(labels).value_counts().to_dict(),
        "attempted_values": pd.Series(attempted).value_counts().to_dict(),
        "attack_flows_not_attempted": int(is_attack.sum()),
    }
    crosstab = pd.crosstab(frame["label"], frame["attempted"])
    invalid = invalid[(invalid > 0).any(axis=1)]
    return summary, crosstab, by_hour, invalid, columns


def main() -> None:
    folder = load_cicids2017_dir()
    OUT.mkdir(parents=True, exist_ok=True)

    summaries, crosstabs, hours, invalids = {}, [], [], []
    columns_by_day = {}
    for day in DAYS:
        path = folder / f"{day}.csv"
        print("Profiling", path)
        summary, crosstab, by_hour, invalid, columns = profile_day(path)
        summaries[day] = summary
        columns_by_day[day] = columns
        crosstabs.append(crosstab.assign(day=day))
        hours.append(by_hour.assign(day=day))
        invalids.append(invalid.assign(day=day))

    first = columns_by_day[DAYS[0]]
    same_columns = all(cols == first for cols in columns_by_day.values())

    labels_by_day = pd.DataFrame({d: s["labels"] for d, s in summaries.items()}).fillna(0)
    labels_by_day = labels_by_day.astype(int)
    labels_by_day.to_csv(OUT / "labels_by_day.csv", lineterminator="\n")
    pd.concat(crosstabs).to_csv(OUT / "attempted.csv", lineterminator="\n")
    pd.concat(hours).to_csv(OUT / "attacks_by_hour.csv", index=False, lineterminator="\n")
    pd.concat(invalids).to_csv(OUT / "invalid_values.csv", lineterminator="\n")

    result = {
        "folder": str(folder),
        "same_columns_every_day": same_columns,
        "columns": first,
        "days": summaries,
        "total_rows": int(sum(s["rows"] for s in summaries.values())),
        "provenance": run_metadata(),
    }
    with open(OUT / "summary.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, default=str)

    print("\nSame columns every day:", same_columns)
    for day, s in summaries.items():
        print(
            f"\n{day}: {s['rows']:,} rows | {s['time_min']} -> {s['time_max']} | "
            f"in time order: {s['rows_in_time_order']} | duplicate ids: {s['duplicate_ids']} | "
            f"unparsed timestamps: {s['unparsed_timestamps']}"
        )
        print("  labels:", s["labels"])
        print("  attempted:", s["attempted_values"])
    print("\nInvalid values (columns with any NaN / inf / negative):")
    print(pd.concat(invalids).to_string())
    print(f"\nSaved to {OUT}")


if __name__ == "__main__":
    main()
