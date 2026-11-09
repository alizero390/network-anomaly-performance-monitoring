"""Compare the attack-share findings across all runs.

Usage:  python scripts/compare_runs.py

Reads the baseline (results/attack_share/) and every results/runs/<run>/attack_share/,
and writes results/comparison.md and results/comparison.csv.
"""

from __future__ import annotations

import json
import math

import pandas as pd

from nadmon.config import PROJECT_DIR

RESULTS = PROJECT_DIR / "results"
LOW_SHARE_PERCENT = 12


def _get(data: dict, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or key not in data or data[key] is None:
            return default
        data = data[key]
    return data


def _alarms(folder, metric: str, reference: str):
    table = pd.read_csv(folder / "alarms_on_validation.csv")
    row = table[(table["metric"] == metric) & (table["reference"] == reference)]
    return int(row["confirmed_alarm_windows"].iloc[0]) if len(row) else None


def _sim_alarm(folder, metric: str, share: float):
    table = pd.read_csv(folder / "resampling_alarm_rates.csv")
    row = table[(table["metric"] == metric) & (table["target_share"].round(3) == share)]
    return float(row["stream_alarm_rate"].iloc[0]) if len(row) else None


def collect(name: str, folder, model_summary: dict) -> dict:
    s = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    obs, cats = s["observed"], s.get("categories") or {}
    per_cat = {c["AttackCategory"]: c for c in cats.get("categories", [])}
    misses = cats.get("share_of_misses", {})
    low_high = obs["low_vs_high_share"]
    gap = cats.get("recall_gap_decomposition")
    fuzz = cats.get("fuzzers_recall_by_period") or {}

    return {
        "run": name,
        "validation records": model_summary.get("validation_records")
        or _get(model_summary, "split", "validation_end", default=0)
        - _get(model_summary, "split", "train_end", default=0),
        "validation attack share": obs["pooled"]["attack_share"],
        "F1 (pooled)": model_summary.get("f1"),
        "recall (pooled)": obs["pooled"]["recall"],
        "FPR (pooled)": obs["pooled"]["fpr"],
        "windows": obs["windows"],
        f"windows with attack share < {LOW_SHARE_PERCENT}%": low_high["n_low"],
        "R2 of window F1: attack share only": obs["f1_decomposition"]["r2_share_only"],
        "R2 of window F1: recall/FPR only": obs["f1_decomposition"]["r2_performance_only"],
        "Spearman window F1 vs attack share": obs["spearman_with_attack_share"]["f1"],
        "Spearman window recall vs attack share": obs["spearman_with_attack_share"]["recall"],
        "mean window recall, low / high share": (
            low_high["low_mean"]["recall"],
            low_high["high_mean"]["recall"],
        ),
        "Generic share of attacks": cats.get("easy_share_of_attacks"),
        "recall excluding Generic": cats.get("recall_excluding_easy"),
        "Fuzzers recall": _get(per_cat, "Fuzzers", "recall"),
        "Fuzzers share of missed attacks": misses.get("Fuzzers"),
        "R2 of window recall: category mix": cats.get("r2_recall_explained_by_category_mix"),
        "recall gap low/high share": _get(gap or {}, "gap"),
        "  of which category mix": _get(gap or {}, "from_category_mix"),
        "  of which within categories": _get(gap or {}, "from_within_category"),
        "Fuzzers recall: first 10 / middle / last 9 windows": tuple(
            _get(fuzz, p, "recall") for p in ("start", "middle", "end")
        )
        if fuzz
        else None,
        "F1 alarms, reference = first 10 windows": _alarms(folder, "f1", "first_10_windows_mean"),
        "F1 alarms, reference = all windows": _alarms(folder, "f1", "all_validation_windows_mean"),
        "calibrated F1 alarms, reference = all windows": _alarms(
            folder, "f1_calibrated", "all_validation_windows_mean"
        ),
        "simulated F1 alarm rate at 1% attacks": _sim_alarm(folder, "f1", 0.01),
        "simulated calibrated-F1 alarm rate at 1% attacks": _sim_alarm(
            folder, "f1_calibrated", 0.01
        ),
        "simulated balanced-accuracy alarm rate at 1% attacks": _sim_alarm(
            folder, "balanced_accuracy", 0.01
        ),
    }


def fmt(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    if isinstance(value, tuple):
        return " / ".join(fmt(v) for v in value)
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def main() -> None:
    rows = []
    baseline = RESULTS / "attack_share"
    if (baseline / "summary.json").is_file():
        model = json.loads((RESULTS / "baseline_summary.json").read_text(encoding="utf-8"))
        rows.append(collect("feb_rf (baseline)", baseline, model))

    for run_dir in sorted((RESULTS / "runs").glob("*")):
        folder = run_dir / "attack_share"
        if (folder / "summary.json").is_file():
            model = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            rows.append(collect(run_dir.name, folder, model))

    if not rows:
        raise SystemExit("No analysed runs found.")

    table = pd.DataFrame(rows).set_index("run").T
    table.to_csv(RESULTS / "comparison.csv", lineterminator="\n")

    lines = [
        "# Comparison across runs",
        "",
        "Generated by `scripts/compare_runs.py`. Runs: `<session>_<model>`; sessions feb "
        "(February 18) and jan (January 22-23); models rf (Random Forest) and hgb "
        "(histogram gradient boosting). Each run uses its own session's validation partition.",
        "",
        "| Measure | " + " | ".join(table.columns) + " |",
        "|---|" + "---:|" * len(table.columns),
    ]
    for measure, values in table.iterrows():
        lines.append(f"| {measure} | " + " | ".join(fmt(v) for v in values) + " |")
    (RESULTS / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
