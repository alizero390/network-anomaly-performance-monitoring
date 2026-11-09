"""Attribute each Strategy B alarm window to a cause.

Usage:  python scripts/attribute_alarms.py

Works on committed outputs only (no raw data): for the baseline and every
results/runs/<run>/attack_share/, it re-applies the alarm rule of
analyze_attack_share.py and labels every flagged window (eligible, at least DROP
below the reference) with one cause:

    too_few_attacks      undetermined: fewer attacks than needed for recall noise to stay below
                         DROP: n_min = ceil(r(1-r)/DROP^2), r = the run's pooled recall
    missed_attacks       window recall is at least DROP below the recall reference;
                         the category with the most missed attacks is reported,
                         with whether the model saw it in training
    false_positive_burst recall is fine but FPR is above max(2 x pooled FPR, 0.5%)
    attack_share_effect  the metric fell while recall and FPR stayed normal

The rule order above decides ties. Writes results/alarm_attribution/:
    <run>.csv     one row per flagged window, metric and reference
    summary.csv   confirmed alarms per run, metric, reference and cause
    summary.md    the same as a readable table
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from nadmon.config import PROJECT_DIR

RESULTS = PROJECT_DIR / "results"
OUT = RESULTS / "alarm_attribution"
DROP = 0.05
CONSECUTIVE = 2
REFERENCE_WINDOWS = 10
METRICS = ("f1", "mcc", "balanced_accuracy", "recall")
FP_BURST_MIN = 0.005
CAUSES = ("missed_attacks", "false_positive_burst", "too_few_attacks", "attack_share_effect")


def run_folders() -> list[tuple[str, object, object]]:
    """(name, attack_share folder, model summary path)."""
    found = []
    if (RESULTS / "attack_share" / "window_metrics_extended.csv").is_file():
        found.append(("feb_rf", RESULTS / "attack_share", RESULTS / "baseline_summary.json"))
    for run_dir in sorted((RESULTS / "runs").glob("*")):
        folder = run_dir / "attack_share"
        if (folder / "window_metrics_extended.csv").is_file():
            found.append((run_dir.name, folder, run_dir / "summary.json"))
    return found


def references(values: np.ndarray) -> dict[str, tuple[float, int]]:
    """Same references as analyze_attack_share.py: (value, first monitored index)."""
    with np.errstate(all="ignore"):
        first = values[:REFERENCE_WINDOWS]
        first_ref = float(np.nanmean(first)) if np.isfinite(first).any() else float("nan")
    return {
        "first_10_windows_mean": (first_ref, REFERENCE_WINDOWS),
        "all_validation_windows_mean": (float(np.nanmean(values)), 0),
    }


def confirmed_windows(values: np.ndarray, ref: float, start: int) -> tuple[list[int], list[int]]:
    """Flagged and confirmed window indices (0-based), skipping ineligible windows."""
    eligible = np.isfinite(values)
    flagged = eligible & (values <= ref - DROP)
    run, flagged_idx, confirmed_idx = 0, [], []
    for i in range(start, len(values)):
        if not eligible[i]:
            continue
        if flagged[i]:
            flagged_idx.append(i)
        run = run + 1 if flagged[i] else 0
        if run >= CONSECUTIVE:
            confirmed_idx.append(i)
    return flagged_idx, confirmed_idx


def attribute(name: str, folder, summary_path) -> pd.DataFrame:
    windows = pd.read_csv(folder / "window_metrics_extended.csv")
    model = json.loads(summary_path.read_text(encoding="utf-8"))
    run_summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    pooled = run_summary["observed"]["pooled"]
    r, pooled_fpr = pooled["recall"], pooled["fpr"]
    n_min = math.ceil(r * (1 - r) / DROP**2) if 0 < r < 1 else 1
    fp_burst = max(2 * pooled_fpr, FP_BURST_MIN)

    trained_on = model.get("training_categories")  # CIC runs record this; UNSW trains on all
    counts_path = folder / "category_window_counts.csv"
    missed_by_window = {}
    if counts_path.is_file():
        counts = pd.read_csv(counts_path)
        counts["missed"] = counts["records"] - counts["detected"]
        top = counts.sort_values("missed", ascending=False).drop_duplicates("window")
        missed_by_window = {
            int(w): (cat, int(m))
            for w, cat, m in top[["window", "AttackCategory", "missed"]].to_numpy()
        }

    recall_refs = references(windows["recall"].to_numpy(dtype=float))
    rows = []
    for metric in METRICS:
        values = windows[metric].to_numpy(dtype=float)
        for ref_name, (ref, start) in references(values).items():
            if not np.isfinite(ref):
                continue
            flagged, confirmed = confirmed_windows(values, ref, start)
            recall_ref = recall_refs[ref_name][0]
            for i in flagged:
                w = windows.iloc[i]
                attacks = int(w["tp"] + w["fn"])
                category, missed = missed_by_window.get(int(w["window"]), (None, 0))
                if attacks < n_min:
                    cause = "too_few_attacks"
                elif np.isfinite(recall_ref) and w["recall"] <= recall_ref - DROP:
                    cause = "missed_attacks"
                elif w["fpr"] > fp_burst:
                    cause = "false_positive_burst"
                else:
                    cause = "attack_share_effect"
                seen = (
                    None
                    if category is None
                    else (True if trained_on is None else category in trained_on)
                )
                rows.append(
                    {
                        "run": name,
                        "metric": metric,
                        "reference": ref_name,
                        "reference_value": ref,
                        "window": int(w["window"]),
                        "start_utc": w["start_utc"],
                        "confirmed": i in confirmed,
                        "value": float(values[i]),
                        "attacks": attacks,
                        "attack_share": float(w["attack_share"]),
                        "recall": float(w["recall"]),
                        "fpr": float(w["fpr"]),
                        "cause": cause,
                        "top_missed_category": category if cause == "missed_attacks" else None,
                        "missed_in_top_category": missed if cause == "missed_attacks" else None,
                        "category_seen_in_training": seen if cause == "missed_attacks" else None,
                        "min_attacks_for_noise": n_min,
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tables = []
    for name, folder, summary_path in run_folders():
        table = attribute(name, folder, summary_path)
        table.to_csv(OUT / f"{name}.csv", index=False, lineterminator="\n")
        tables.append(table)
        # Consistency check against the alarm table written by the analysis.
        alarms = pd.read_csv(folder / "alarms_on_validation.csv")
        for _, a in alarms.iterrows():
            mine = table[
                (table["metric"] == a["metric"])
                & (table["reference"] == a["reference"])
                & table["confirmed"]
            ]
            if len(mine) != int(a["confirmed_alarm_windows"]):
                raise RuntimeError(f"{name} {a['metric']} {a['reference']}: alarm count mismatch")

    data = pd.concat(tables, ignore_index=True)
    confirmed = data[data["confirmed"]]
    summary = (
        confirmed.groupby(["run", "metric", "reference", "cause"])
        .size()
        .unstack("cause", fill_value=0)
        .reindex(columns=list(CAUSES), fill_value=0)
    )
    summary["total"] = summary.sum(axis=1)
    summary.to_csv(OUT / "summary.csv", lineterminator="\n")

    # Distinct windows: one metric and reference, so no window is counted twice.
    recall_alarms = confirmed[
        (confirmed["metric"] == "recall")
        & (confirmed["reference"] == "all_validation_windows_mean")
        & (confirmed["cause"] == "missed_attacks")
    ]
    by_category = (
        recall_alarms.groupby(["run", "top_missed_category", "category_seen_in_training"])
        .size()
        .rename("windows")
        .reset_index()
    )

    lines = [
        "# Alarm attribution",
        "",
        "Generated by `scripts/attribute_alarms.py`. Confirmed Strategy B alarm windows "
        f"(drop >= {DROP} in {CONSECUTIVE} consecutive eligible windows), by cause. "
        "See the script docstring for the cause rules.",
        "",
        "| Run | Metric | Reference | " + " | ".join(CAUSES) + " | Total |",
        "|---|---|---|" + "---:|" * (len(CAUSES) + 1),
    ]
    for (run, metric, ref), row in summary.iterrows():
        cells = " | ".join(str(int(row[c])) for c in CAUSES)
        lines.append(f"| {run} | {metric} | {ref} | {cells} | {int(row['total'])} |")
    lines += [
        "",
        "## Missed-attack alarm windows by category",
        "",
        "Recall, all-window reference; each window counted once. 'Seen in training' compares",
        "exact labels: CIC-IDS-2017's Friday Portscan and DDoS are related to, but not the",
        "same label as, Thursday's Infiltration-Portscan and Wednesday's DoS attacks.",
        "",
        "| Run | Category | Seen in training (exact label) | Confirmed alarm windows |",
        "|---|---|---|---:|",
    ]
    for row in by_category.itertuples(index=False):
        seen = "yes" if row.category_seen_in_training else "no"
        lines.append(f"| {row.run} | {row.top_missed_category} | {seen} | {row.windows} |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
