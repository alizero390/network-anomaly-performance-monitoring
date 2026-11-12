"""Calibrate Strategies A-C on February validation and run the validation experiment.

Usage (repository root, virtual environment active, raw data available):

    python scripts/run_strategy_experiment.py --quick      # about 5-10 minutes, for a first check
    python scripts/run_strategy_experiment.py              # full run: 200 streams per scenario

Needs results/validation_predictions.csv (scripts/baseline.py). Reads the raw February
files for the validation features; never reads the test partition.

Steps (STRATEGY_DESIGN_SPEC.md, RESEARCH_DECISIONS.md section 16):
 1. Validation features, labels, predictions and strata (attack category; benign
    service|proto|state).
 2. Random halves: Strategy A reference sample / stream records (D10).
 3. References from all of validation: calibrated F1 and F1 (D6), n_min (D8).
 4. Scenarios S0, H1-H3, X1-X2 from the stream half; only those with clean ground truth.
 5. Calibration: Strategy A threshold q on S0 streams; association period L per delay on
    X1/X2 streams. Written to configs/strategies.toml (frozen values for the test run).
 6. Grid: every scenario x stream x label condition x strategy (D14).

Outputs in results/strategies/validation[_quick]/:
    calibration.json, scenarios.csv, stream_results.csv.gz, summary.csv, summary.md,
    paired_B_vs_B_F1.csv, paired_C_active_vs_B.csv
The calibrated settings go to configs/strategies.toml (full run only; a quick run
writes strategies_quick.toml in its own folder so the frozen file is never replaced
by quick values).
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace

import numpy as np
import pandas as pd

from nadmon import dataset
from nadmon import evaluation as ev
from nadmon import experiment as ex
from nadmon import scenarios as sc
from nadmon.config import PROJECT_DIR, load_paths
from nadmon.provenance import run_metadata

RESULTS = PROJECT_DIR / "results"
CONFIG = PROJECT_DIR / "configs" / "strategies.toml"


def load_validation() -> ex.Partition:
    paths = load_paths()
    paths.check_raw_files()
    timestamps = dataset.read_february_timestamps(paths.raw_files)
    cutoff = dataset.find_validation_cutoff(timestamps)
    data = dataset.load_train_validation(
        paths.raw_files, cutoff, extra_columns=[dataset.ATTACK_CAT_INDEX]
    )
    X, y = dataset.preprocess(data)
    X_val = X.iloc[dataset.TRAIN_END :].reset_index(drop=True)
    y_val = y[dataset.TRAIN_END :]
    category = dataset.normalize_attack_category(
        data[dataset.ATTACK_CAT_INDEX].iloc[dataset.TRAIN_END :]
    ).to_numpy()

    pred = pd.read_csv(RESULTS / "validation_predictions.csv")
    if len(pred) != len(y_val) or (pred["TrueLabel"].to_numpy() != y_val).any():
        raise SystemExit("validation_predictions.csv does not line up with the raw data.")

    col = dataset.model_column
    strata = sc.unsw_strata(
        y_val,
        category,
        X_val[col(dataset.COLUMN_NAMES.index("service"))],
        X_val[col(dataset.COLUMN_NAMES.index("proto"))],
        X_val[col(dataset.COLUMN_NAMES.index("state"))],
    )
    numeric = tuple(col(i) for i in dataset.NUMERIC_FEATURES)
    categorical = tuple(col(i) for i in dataset.CATEGORICAL_FEATURES)
    return ex.Partition(
        y_val.astype(int),
        pred["Prediction"].to_numpy(dtype=int),
        strata,
        X_val,
        numeric,
        categorical,
    )


def write_config(cal: ex.Calibration, settings: ex.Settings, quick: bool, path) -> None:
    lines = [
        "# Strategy settings calibrated on February validation (STRATEGY_DESIGN_SPEC.md D1).",
        "# Written by scripts/run_strategy_experiment.py. Commit it before any test run;",
        "# the test run must use these values unchanged.",
        'calibrated_on = "February validation"',
        f"quick_run = {str(quick).lower()}",
        "",
        "[reference]",
        f"attack_share = {cal.pi0:.6f}",
        f"recall = {cal.recall:.6f}",
        f"f1_calibrated = {cal.reference_f1_calibrated:.6f}",
        f"f1 = {cal.reference_f1:.6f}",
        "",
        "[strategy_b]",
        f"n_min = {cal.n_min}",
        f"m_min = {settings.m_min}",
        f"max_span = {settings.max_span}",
        f"drop = {settings.drop}",
        f"consecutive = {settings.consecutive}",
        f"rearm = {settings.rearm}",
        "",
        "[strategy_a]",
        f"q = {cal.q if cal.q is not None else 'nan'}",
        f"alpha = {settings.a_alpha}",
        f"consecutive = {settings.a_consecutive}",
        f"reference_size = {settings.a_reference_size}",
        "",
        "[strategy_c.association_period]",
        *[f'"{d}" = {L}' for d, L in sorted(cal.periods.items())],
        "",
        "[streams]",
        f"window_size = {settings.window_size}",
        f"n_windows = {settings.n_windows}",
        f"onset = {settings.onset}",
        f"seed = {settings.seed}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summary_markdown(summary: pd.DataFrame, cal: ex.Calibration, quick: bool) -> str:
    def pct(v):
        return "–" if pd.isna(v) else f"{v:.0%}"

    def num(v):
        return "–" if pd.isna(v) else f"{v:g}"

    lines = [
        f"# Strategy comparison: February validation{' (quick run)' if quick else ''}",
        "",
        "Generated by `scripts/run_strategy_experiment.py`. Rates are over streams; "
        "recall only for harmful scenarios. A uses no labels (condition `inputs`).",
        "",
        f"Calibrated: Strategy A q = {cal.q:.3f}; association period L by delay "
        f"{cal.periods}; n_min = {cal.n_min}; references: calibrated F1 "
        f"{cal.reference_f1_calibrated:.4f}, F1 {cal.reference_f1:.4f}.",
        "",
        "| Scenario | Condition | Strategy | Streams | Event recall | False-alert rate | "
        "Median delay (windows) |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {r.scenario} | {r.condition} | {r.strategy} | {r.streams} | "
            f"{pct(r.event_recall)} | {pct(r.false_alert_rate)} | {num(r.median_delay)} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="20 streams, 20 calibration streams")
    parser.add_argument("--streams", type=int, default=None)
    parser.add_argument("--calibration", type=int, default=None)
    args = parser.parse_args()

    settings = ex.Settings()
    if args.quick:
        settings = replace(settings, n_streams=20, n_calibration=20)
    if args.streams:
        settings = replace(settings, n_streams=args.streams)
    if args.calibration:
        settings = replace(settings, n_calibration=args.calibration)
    out = RESULTS / "strategies" / ("validation_quick" if args.quick else "validation")
    out.mkdir(parents=True, exist_ok=True)
    start = time.time()

    print("1. Loading validation data ...")
    part = load_validation()
    print(f"   {len(part.y)} records, attack share {part.y.mean():.4f}")

    print("2-3. Reference half, stream half, references ...")
    ref_idx, pool_idx = ex.split_validation(len(part.y), settings.seed)
    ref = ex.a_reference(part.subset(ref_idx), settings)
    pool = part.subset(pool_idx)
    cal = ex.base_calibration(part)
    print(f"   n_min {cal.n_min}; reference calibrated F1 {cal.reference_f1_calibrated:.4f}")

    print("4. Scenarios ...")
    rates = sc.stratum_rates(pool.strata, pool.y, pool.p)
    all_scen = sc.standard_scenarios(rates, cal.pi0)
    table = sc.scenario_table(all_scen, rates, cal.pi0)
    table.to_csv(out / "scenarios.csv", index=False, lineterminator="\n")
    usable = set(table.loc[table["usable"], "scenario"])
    scenarios = [s for s in all_scen if s.name in usable]
    print(
        table[["scenario", "intended", "label", "cal_f1_change", "usable"]].to_string(index=False)
    )

    print("5. Calibration ...")
    cal = ex.calibrate(pool, scenarios, cal, settings, ref)
    print(f"   q = {cal.q:.3f}; association periods {cal.periods}")
    config_path = out / "strategies_quick.toml" if args.quick else CONFIG
    write_config(cal, settings, args.quick, config_path)
    (out / "calibration.json").write_text(
        json.dumps(
            {"calibration": cal.to_dict(), "settings": settings.__dict__, **run_metadata()},
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    print("6. Grid ...")
    results = ex.run_grid(pool, scenarios, cal, settings, ref)
    results.to_csv(out / "stream_results.csv.gz", index=False, lineterminator="\n")
    summary = ev.summarise(results, ["scenario", "condition", "strategy"])
    summary.to_csv(out / "summary.csv", index=False, lineterminator="\n")
    for a, b in (("B", "B_F1"), ("C_active", "B")):
        ev.paired_comparison(results, a, b).to_csv(
            out / f"paired_{a}_vs_{b}.csv", index=False, lineterminator="\n"
        )
    (out / "summary.md").write_text(summary_markdown(summary, cal, args.quick), encoding="utf-8")

    overview = ev.summarise(
        results[~results["condition"].str.contains("alert_first")], ["scenario", "strategy"]
    )
    print("\nOverview (random-label conditions pooled):")
    cols = ["scenario", "strategy", "event_recall", "false_alert_rate", "median_delay"]
    print(overview[cols].round(3).to_string(index=False))
    print(f"\nDone in {(time.time() - start) / 60:.1f} minutes. Outputs in {out}")
    print(f"Calibrated settings written to {config_path}")
    np.seterr(all="warn")


if __name__ == "__main__":
    main()
