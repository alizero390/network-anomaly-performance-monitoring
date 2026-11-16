"""Label-bias study on CIC-IDS-2017 Friday in time order (D20, Paper 2).

Usage (repository root, virtual environment active):

    python scripts/run_label_bias_cic.py --model rf     # a few minutes
    python scripts/run_label_bias_cic.py --model hgb

Needs results/runs/cic2_<model>/validation_predictions.csv and monitor_predictions.csv
(from scripts/train_cicids2017.py --split cic2). Nothing is calibrated on Friday: the
detector's reference comes from the validation half of Thursday, every other setting
from the frozen configs/strategies.toml, and the label conditions from
src/nadmon/label_bias.py.

Outputs in results/label_bias/cic2_<model>/: windows.csv (ground truth per window),
events.csv, draws.csv.gz (one row per draw, condition and strategy), policy_table.csv,
summary.md, run.json
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace

import pandas as pd

from nadmon import experiment as ex
from nadmon import frozen
from nadmon import label_bias as lbs
from nadmon import natural_bias as nb
from nadmon.config import PROJECT_DIR
from nadmon.provenance import run_metadata

RESULTS = PROJECT_DIR / "results"
CONFIG = PROJECT_DIR / "configs" / "strategies.toml"


def load(run_dir, name: str) -> pd.DataFrame:
    path = run_dir / f"{name}_predictions.csv"
    if not path.is_file():
        raise SystemExit(f"{path} is missing. Run scripts/train_cicids2017.py --split cic2 first.")
    return pd.read_csv(path, usecols=["TrueLabel", "Prediction", "AttackCategory", "Timestamp"])


def reference(frozen_cal: ex.Calibration, validation: pd.DataFrame) -> ex.Calibration:
    y = validation["TrueLabel"].to_numpy(dtype=int)
    cal = lbs.model_reference(frozen_cal, y, validation["Prediction"].to_numpy(dtype=int))
    return replace(cal, pi0=float(y.mean()))


def window_table(friday: pd.DataFrame, truth: nb.Truth, window_size: int) -> pd.DataFrame:
    rows = []
    for w in range(len(truth.calibrated)):
        part = friday.iloc[w * window_size : (w + 1) * window_size]
        attacks = part[part["TrueLabel"] == 1]
        rows.append(
            {
                "window": w,
                "start": pd.to_datetime(part["Timestamp"].iloc[0], unit="s"),
                "attacks": len(attacks),
                "categories": " ".join(sorted(attacks["AttackCategory"].unique())),
                "recall": attacks["Prediction"].mean() if len(attacks) else float("nan"),
                "calibrated_f1": truth.calibrated[w],
                "defined": bool(truth.defined[w]),
                "harmful": bool(truth.harmful[w]),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["rf", "hgb"], required=True)
    parser.add_argument("--draws", type=int, default=200)
    args = parser.parse_args()
    start = time.time()

    run_name = f"cic2_{args.model}"
    run_dir = RESULTS / "runs" / run_name
    out = RESULTS / "label_bias" / run_name
    out.mkdir(parents=True, exist_ok=True)
    cfg = frozen.read_config(CONFIG)
    settings = frozen.settings_from_config(cfg)

    print(f"1. Reference from the validation half of Thursday ({run_name}) ...")
    cal = reference(frozen.calibration_from_config(cfg), load(run_dir, "validation"))
    print(
        f"   recall {cal.recall:.4f}, n_min {cal.n_min}, calibrated F1 "
        f"{cal.reference_f1_calibrated:.4f}, reference share {cal.pi0:.3f}"
    )

    print("2. Friday ground truth ...")
    friday = load(run_dir, "monitor")
    y = friday["TrueLabel"].to_numpy(dtype=int)
    p = friday["Prediction"].to_numpy(dtype=int)
    truth = nb.window_truth(y, p, settings.window_size, cal)
    windows = window_table(friday, truth, settings.window_size)
    windows.to_csv(out / "windows.csv", index=False, lineterminator="\n")
    events = pd.DataFrame(
        [
            {
                "event": i + 1,
                "first_window": a,
                "last_window": b,
                "start": windows.loc[a, "start"],
                "categories": " ".join(
                    sorted(set(" ".join(windows.loc[a:b, "categories"]).split()))
                ),
                "median_calibrated_f1": float(windows.loc[a:b, "calibrated_f1"].median()),
            }
            for i, (a, b) in enumerate(truth.events)
        ]
    )
    events.to_csv(out / "events.csv", index=False, lineterminator="\n")
    print(
        f"   {len(windows)} windows, {int(truth.defined.sum())} defined, "
        f"{int(truth.harmful.sum())} harmful, {len(truth.events)} events"
    )
    if len(events):
        print(events.to_string(index=False))

    conditions = lbs.policy_conditions()
    print(f"3. {len(conditions)} label conditions x {args.draws} draws ...")
    rows = []
    for k, cond in enumerate(conditions):
        for d in range(args.draws):
            seed = settings.seed + 1000 * (k + 1) + d
            for r in nb.run_condition(y, p, cond, cal, settings, truth, seed):
                rows.append({**r, "draw": d})
        if (k + 1) % 8 == 0:
            print(f"   {k + 1}/{len(conditions)} conditions")
    draws = pd.DataFrame(rows)
    draws.to_csv(out / "draws.csv.gz", index=False, lineterminator="\n")
    table = nb.policy_table(draws)
    parsed = pd.DataFrame([lbs.parse_condition(c) for c in table["condition"]])
    table = pd.concat([table[["condition"]], parsed, table.drop(columns="condition")], axis=1)
    table.to_csv(out / "policy_table.csv", index=False, lineterminator="\n")

    info = {
        "run": run_name,
        "draws": args.draws,
        "conditions": len(conditions),
        "recall": cal.recall,
        "n_min": cal.n_min,
        "reference_f1_calibrated": cal.reference_f1_calibrated,
        "reference_share": cal.pi0,
        "windows": len(windows),
        "events": len(truth.events),
        "config_sha256": frozen.config_hash(CONFIG),
        "minutes": round((time.time() - start) / 60, 1),
        **run_metadata(),
    }
    (out / "run.json").write_text(json.dumps(info, indent=2, default=str) + "\n", encoding="utf-8")

    def pct(v):
        return "–" if pd.isna(v) else f"{v:.0%}"

    lines = [
        f"# Label-bias study on CIC-IDS-2017 Friday: {run_name}",
        "",
        f"Generated by `scripts/run_label_bias_cic.py` (D20). {len(truth.events)} harmful "
        f"events in {len(windows)} windows; {args.draws} label draws per condition.",
        "",
        "| Condition | Weights | Strategy | Events detected | Draws with a false alarm | "
        "Median delay |",
        "|---|---|---|---:|---:|---:|",
    ]
    for r in table.itertuples(index=False):
        delay = "–" if pd.isna(r.median_delay) else f"{r.median_delay:g}"
        lines.append(
            f"| {r.condition} | {r.weights} | {r.strategy} | {pct(r.detection_rate)} | "
            f"{pct(r.any_false_alarm)} | {delay} |"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    pd.set_option("display.width", 220)
    show = table[table["weights"] == "correct"].pivot_table(
        index="condition",
        columns="strategy",
        values=["detection_rate", "any_false_alarm"],
        sort=False,
    )
    print("\nEvents detected and draws with a false alarm:")
    print(show.round(3).to_string())
    wrong = table[(table["weights"] != "correct") & table["strategy"].str.startswith("B_ipw")]
    print("\nWrong weights:")
    print(
        wrong[["condition", "strategy", "detection_rate", "any_false_alarm", "median_delay"]]
        .round(3)
        .to_string(index=False)
    )
    print(f"\nDone in {info['minutes']} minutes. Outputs in {out}")


if __name__ == "__main__":
    main()
