"""Describe where attacks occur over time in the January session.

Usage:  python scripts/describe_session.py

Reads only Stime, attack_cat and Label of the January 22-23 session (no features),
in stable time order, and writes to results/sessions/jan/:
    timeline.csv      one row per 5,000-record window: time, attack share, categories
    summary.json      attack positions as fractions of the session, and per partition
    timeline.png/pdf  attack share and categories over the session

Inspecting the whole January session, including the part that would have been its
test set, was approved on 2026-11-08 (RESEARCH_DECISIONS.md, section 13): January is
a replication-only session with no held-out test. February is deliberately not
supported here, so February test labels are never read.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nadmon import dataset, sessions
from nadmon.config import load_paths
from nadmon.provenance import run_metadata

SESSION = sessions.JANUARY
WINDOW = dataset.WINDOW_SIZE
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8f5bd6", "#d6457a", "#5bb8d6"]
INK_2, GRID = "#52514e", "#e4e3df"


def load_labels(files) -> pd.DataFrame:
    columns = [dataset.STIME_INDEX, dataset.ATTACK_CAT_INDEX, dataset.LABEL_INDEX]
    parts = []
    for file in files:
        print("Reading labels:", file.name)
        for chunk in pd.read_csv(
            file, header=None, usecols=columns, chunksize=200_000, low_memory=False
        ):
            stime = chunk[dataset.STIME_INDEX]
            selected = chunk[(stime >= SESSION.start) & (stime < SESSION.end)]
            if not selected.empty:
                parts.append(selected)
    data = pd.concat(parts, ignore_index=True)
    data = data.sort_values(by=dataset.STIME_INDEX, kind="stable").reset_index(drop=True)
    data["category"] = dataset.normalize_attack_category(data[dataset.ATTACK_CAT_INDEX])
    data["label"] = data[dataset.LABEL_INDEX].astype(int)
    return data[[dataset.STIME_INDEX, "category", "label"]]


def main() -> None:
    paths = load_paths()
    paths.check_raw_files()
    out = paths.results_dir / "sessions" / SESSION.name
    out.mkdir(parents=True, exist_ok=True)

    data = load_labels(paths.raw_files)
    n = len(data)
    # Data are already in stable time order, so labels line up with timestamps.
    split = sessions.split_session(
        data[dataset.STIME_INDEX].to_numpy(), SESSION, data["label"].to_numpy()
    )
    labels = data["label"].to_numpy()
    attack_pos = np.flatnonzero(labels == 1)
    print(f"January records: {n:,}  attacks: {len(attack_pos):,} ({labels.mean():.2%})")

    # Per-window timeline over the whole session.
    data["window"] = np.arange(n) // WINDOW + 1
    attacks = data[data["label"] == 1]
    by_cat = pd.crosstab(attacks["window"], attacks["category"]).reindex(
        range(1, data["window"].max() + 1), fill_value=0
    )
    timeline = (
        data.groupby("window")
        .agg(
            records=("label", "size"),
            attacks=("label", "sum"),
            start_ts=(dataset.STIME_INDEX, "min"),
            end_ts=(dataset.STIME_INDEX, "max"),
        )
        .join(by_cat)
    )
    timeline["attack_share"] = timeline["attacks"] / timeline["records"]
    timeline["start_utc"] = pd.to_datetime(timeline["start_ts"], unit="s", utc=True)
    first_record = (timeline.index - 1) * WINDOW
    timeline["partition"] = np.select(
        [first_record < split.train_end, first_record < split.validation_end],
        ["train", "validation"],
        "after_validation",
    )
    timeline.to_csv(out / "timeline.csv", lineterminator="\n")

    def partition_stats(lo: int, hi: int) -> dict:
        part = data.iloc[lo:hi]
        att = part[part["label"] == 1]
        return {
            "records": int(len(part)),
            "attacks": int(len(att)),
            "attack_share": float(part["label"].mean()),
            "categories": att["category"].value_counts().to_dict(),
        }

    quantiles = (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1)
    summary = {
        "records": n,
        "attacks": int(len(attack_pos)),
        "attack_share": float(labels.mean()),
        "categories": data.loc[data["label"] == 1, "category"].value_counts().to_dict(),
        "session_utc": [
            str(pd.to_datetime(data[dataset.STIME_INDEX].iloc[0], unit="s", utc=True)),
            str(pd.to_datetime(data[dataset.STIME_INDEX].iloc[-1], unit="s", utc=True)),
        ],
        "attack_position_quantiles_as_session_fraction": {
            str(q): float(attack_pos[int(q * (len(attack_pos) - 1))] / n) for q in quantiles
        },
        "windows_with_attacks": int((timeline["attacks"] > 0).sum()),
        "windows": int(len(timeline)),
        "split_rule": SESSION.rule,
        "split": {
            "train": partition_stats(0, split.train_end),
            "validation": partition_stats(split.train_end, split.validation_end),
            "after_validation": partition_stats(split.validation_end, n),
        },
        "provenance": run_metadata(),
    }
    with open(out / "summary.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, default=str)

    # Figure: attack records per window, stacked by category.
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    bottom = np.zeros(len(timeline))
    cats = by_cat.sum().sort_values(ascending=False).index
    for i, cat in enumerate(cats):
        color = COLORS[i] if i < len(COLORS) else INK_2
        label = cat if i < len(COLORS) else None
        ax.bar(timeline.index, timeline[cat], bottom=bottom, width=0.9, color=color, label=label)
        bottom += timeline[cat].to_numpy()
    for boundary, name in (
        (split.train_end, "train end"),
        (split.validation_end, "validation end"),
    ):
        x = boundary / WINDOW + 0.5
        ax.axvline(x, color=INK_2, linewidth=0.8, linestyle=":")
        ax.text(x, ax.get_ylim()[1] * 0.95, f" {name}", color=INK_2, fontsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_xlabel(f"January window ({WINDOW:,} records each)")
    ax.set_ylabel("Attack records")
    ax.set_title("Attacks over the January session", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / f"timeline.{ext}", dpi=300, bbox_inches="tight")

    print(
        json.dumps({k: v for k, v in summary.items() if k != "provenance"}, indent=2, default=str)
    )
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
