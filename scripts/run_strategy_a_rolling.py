"""Strategy A with a moving reference (decision D21): validation calibration and test run.

Usage (repository root, virtual environment active, raw data available):

    python scripts/run_strategy_a_rolling.py --partition validation --quick   # first check
    python scripts/run_strategy_a_rolling.py --partition validation           # calibrate + run
    (commit configs/strategy_a_rolling.toml in GitHub Desktop)
    python scripts/run_strategy_a_rolling.py --partition test --check-only     # guards only
    python scripts/run_strategy_a_rolling.py --partition test --confirm-committed

Every other setting comes unchanged from the frozen configs/strategies.toml. The streams
and label draws are those of the earlier strategy runs (results/strategies/<partition>),
so B is reproduced exactly (checked and printed) and the new variants are paired with
B and with the earlier fixed-reference A and C_active.

Validation (D21): q_rolling and q_anchored on 100 stable streams (at most 5% with a
warning), the association period L per delay on harmful streams; written to
configs/strategy_a_rolling.toml. Test (once, nothing calibrated): guards as in
scripts/run_strategy_test.py; the config must be committed.

Outputs in results/strategy_a_rolling/<partition>[_quick]/: calibration.json (validation),
run.json, stream_results.csv.gz, summary.csv, summary.md, paired_*.csv, natural.csv.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace

import joblib
import numpy as np
import pandas as pd

from nadmon import evaluation as ev
from nadmon import experiment as ex
from nadmon import february, frozen
from nadmon import rolling_a as ra
from nadmon import scenarios as sc
from nadmon.config import PROJECT_DIR, load_paths
from nadmon.provenance import run_metadata

RESULTS = PROJECT_DIR / "results"
BASE_CONFIG = PROJECT_DIR / "configs" / "strategies.toml"
CONFIG = PROJECT_DIR / "configs" / "strategy_a_rolling.toml"
OUT_ROOT = RESULTS / "strategy_a_rolling"
EARLIER = RESULTS / "strategies"


# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------


def write_config(rc: ra.RollingCalibration, quick: bool, path) -> None:
    lines = [
        "# Strategy A with a moving reference (RESEARCH_DECISIONS.md D21), calibrated on",
        "# February validation by scripts/run_strategy_a_rolling.py. Commit it before the",
        "# test run; the test run must use these values unchanged.",
        f'base_config_sha256 = "{frozen.config_hash(BASE_CONFIG)}"',
        f"quick_run = {str(quick).lower()}",
        "",
        "[a_rolling]",
        f"lookback = {rc.lookback}",
        f"gap = {rc.gap}",
        f"q = {rc.q_rolling}",
        "",
        "[a_anchored]",
        f'calibrated_under = "{ra.ANCHORED_CALIBRATION}"',
        f"q = {rc.q_anchored}",
        "",
        "[c_active_rolling.association_period]",
        *[f'"{d}" = {L}' for d, L in sorted(rc.periods.items())],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_config(cfg: dict) -> ra.RollingCalibration:
    return ra.RollingCalibration(
        lookback=int(cfg["a_rolling"]["lookback"]),
        gap=int(cfg["a_rolling"]["gap"]),
        q_rolling=float(cfg["a_rolling"]["q"]),
        q_anchored=float(cfg["a_anchored"]["q"]),
        periods={int(k): int(v) for k, v in cfg["c_active_rolling"]["association_period"].items()},
    )


def test_guards(args) -> ra.RollingCalibration:
    if not CONFIG.is_file():
        raise SystemExit(f"{CONFIG} not found: run --partition validation (full) first.")
    cfg = frozen.read_config(CONFIG)
    if cfg.get("quick_run", True):
        raise SystemExit("configs/strategy_a_rolling.toml comes from a quick run.")
    if cfg.get("base_config_sha256") != frozen.config_hash(BASE_CONFIG):
        raise SystemExit("configs/strategies.toml changed since the D21 calibration.")
    rc = read_config(cfg)
    saved = json.loads((OUT_ROOT / "validation" / "calibration.json").read_text(encoding="utf-8"))
    saved = saved["calibration"]
    if (
        not np.isclose(saved["q_rolling"], rc.q_rolling)
        or not np.isclose(saved["q_anchored"], rc.q_anchored)
        or {int(k): int(v) for k, v in saved["periods"].items()} != rc.periods
    ):
        raise SystemExit("The config differs from results/strategy_a_rolling/validation.")
    committed = frozen.committed_unchanged(CONFIG, PROJECT_DIR)
    if committed is False:
        raise SystemExit("configs/strategy_a_rolling.toml has uncommitted changes. Commit it.")
    if committed is None and not args.confirm_committed and not args.check_only:
        raise SystemExit(
            "git is not available here. Commit configs/strategy_a_rolling.toml in GitHub "
            "Desktop, then run again with --confirm-committed."
        )
    run_json = OUT_ROOT / "test" / "run.json"
    if run_json.is_file():
        previous = json.loads(run_json.read_text(encoding="utf-8"))
        if not args.resume_identical:
            raise SystemExit("A D21 test run already exists: the test partition is used once.")
        if previous.get("config_sha256") != frozen.config_hash(CONFIG):
            raise SystemExit("The config changed since the earlier test run: not allowed.")
    return rc


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------


def load_validation() -> ex.Partition:
    X, y, category = february.load_frames(load_paths(), "validation")
    pred = pd.read_csv(RESULTS / "validation_predictions.csv")
    if len(pred) != len(y) or (pred["TrueLabel"].to_numpy() != y).any():
        raise SystemExit("validation_predictions.csv does not line up with the raw data.")
    return february.partition(X, y, category, pred["Prediction"].to_numpy())


def load_test() -> ex.Partition:
    paths = load_paths()
    X, y, category = february.load_frames(paths, "test")
    model = joblib.load(paths.models_dir / "random_forest_baseline.joblib")
    pred = model.predict(X).astype(int)
    return february.partition(X, y, category, pred)


def scenarios_for(pool: ex.Partition, cal: ex.Calibration, out):
    rates = sc.stratum_rates(pool.strata, pool.y, pool.p)
    base = sc.standard_scenarios(rates, cal.pi0)
    base_ok = set(sc.scenario_table(base, rates, cal.pi0).query("usable")["scenario"])
    all_scen = base + sc.harder_variants([x for x in base if x.name in base_ok])
    table = sc.scenario_table(all_scen, rates, cal.pi0)
    table.to_csv(out / "scenarios.csv", index=False, lineterminator="\n")
    usable = set(table.loc[table["usable"], "scenario"])
    scenarios = [x for x in all_scen if x.name in usable]
    base_scenarios = [x for x in scenarios if x.ramp == 0 and not x.name.endswith("_rare")]
    return scenarios, base_scenarios


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------


def check_b_reproduced(results: pd.DataFrame, partition: str, n_streams: int) -> str:
    path = EARLIER / partition / "stream_results.csv.gz"
    if not path.is_file():
        return f"not checked ({path} missing)"
    old = pd.read_csv(path)
    key = ["scenario", "stream", "condition"]
    cols = ["detected", "detection_delay", "false_alerts", "alarms"]
    old = old[(old["strategy"] == "B") & (old["stream"] < n_streams)].set_index(key)[cols]
    new = results[results["strategy"] == "B"].set_index(key)[cols]
    joined = new.join(old, rsuffix="_old", how="inner")
    if len(joined) != len(new):
        return f"partly checked ({len(joined)} of {len(new)} rows found in the earlier run)"
    same = all(
        np.allclose(joined[c].astype(float), joined[c + "_old"].astype(float), equal_nan=True)
        for c in cols
    )
    return "identical to the earlier run" if same else "DIFFERENT from the earlier run"


def earlier_rows(partition: str, n_streams: int) -> pd.DataFrame:
    path = EARLIER / partition / "stream_results.csv.gz"
    if not path.is_file():
        return pd.DataFrame()
    old = pd.read_csv(path)
    return old[old["strategy"].isin(["A", "C_active"]) & (old["stream"] < n_streams)]


def summary_markdown(summary, natural, rc, partition, b_check, quick) -> str:
    def pct(v):
        return "–" if pd.isna(v) else f"{v:.0%}"

    def num(v):
        return "–" if pd.isna(v) else f"{v:g}"

    lines = [
        f"# Strategy A with a moving reference (D21): February {partition}"
        + (" (quick run)" if quick else ""),
        "",
        "Generated by `scripts/run_strategy_a_rolling.py`. A_rolling compares each window "
        f"with windows w-{rc.gap + rc.lookback - 1}..w-{rc.gap}; A_anchored with the "
        f"{rc.lookback} most recent windows Strategy B judged healthy (conditions "
        f"{', '.join(ra.ANCHORED_CONDITIONS)} only). A and C_active are the earlier "
        "fixed-reference results on the same streams, for comparison.",
        "",
        f"Calibrated on validation: q_rolling = {rc.q_rolling:.3f}, q_anchored = "
        f"{rc.q_anchored:.3f}, association period L by delay {rc.periods}.",
        "",
        f"Strategy B on these streams: {b_check}.",
        "",
        "| Scenario | Condition | Strategy | Streams | Event recall | False-alert rate | "
        "Median delay |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {r.scenario} | {r.condition} | {r.strategy} | {r.streams} | "
            f"{pct(r.event_recall)} | {pct(r.false_alert_rate)} | {num(r.median_delay)} |"
        )
    lines += [
        "",
        f"## Real {partition} windows in time order (no injected change)",
        "",
        "| Strategy | Condition | Windows | Alarms | Alarm windows (1-based) |",
        "|---|---|---:|---:|---|",
    ]
    for r in natural.itertuples(index=False):
        lines.append(
            f"| {r.strategy} | {r.condition} | {r.windows} | {r.alarms} | {r.alarm_windows} |"
        )
    return "\n".join(lines) + "\n"


def report(results, natural, rc, partition, settings, out, quick) -> None:
    b_check = check_b_reproduced(results, partition, settings.n_streams)
    print(f"   Strategy B: {b_check}")
    combined = pd.concat([results, earlier_rows(partition, settings.n_streams)], ignore_index=True)
    combined.to_csv(out / "stream_results.csv.gz", index=False, lineterminator="\n")
    summary = ev.summarise(combined, ["scenario", "condition", "strategy"])
    summary.to_csv(out / "summary.csv", index=False, lineterminator="\n")
    pairs = [("C_active_rolling", "B"), ("A_rolling", "A"), ("C_active_rolling", "C_active")]
    for a, b in pairs:  # A and A_rolling are label-free: both have condition "inputs"
        if {a, b} <= set(combined["strategy"]):
            ev.paired_comparison(combined, a, b).to_csv(
                out / f"paired_{a}_vs_{b}.csv", index=False, lineterminator="\n"
            )
    natural.to_csv(out / "natural.csv", index=False, lineterminator="\n")
    (out / "summary.md").write_text(
        summary_markdown(summary, natural, rc, partition, b_check, quick), encoding="utf-8"
    )
    random = combined[~combined["condition"].str.contains("alert_first")]
    overview = ev.summarise(random, ["scenario", "strategy"])
    cols = ["scenario", "strategy", "event_recall", "false_alert_rate", "median_delay"]
    print("\nOverview (random-label conditions pooled; A variants on inputs):")
    print(overview[cols].round(3).to_string(index=False))
    print("\nReal windows in time order:")
    print(natural[["strategy", "condition", "alarms", "alarm_windows"]].to_string(index=False))


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", choices=["validation", "test"], required=True)
    parser.add_argument("--quick", action="store_true", help="validation: 20 streams")
    parser.add_argument("--streams", type=int, default=None)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--confirm-committed", action="store_true")
    parser.add_argument("--resume-identical", action="store_true")
    args = parser.parse_args()
    if args.partition == "test" and args.quick:
        raise SystemExit("--quick is for validation only.")

    base_cfg = frozen.read_config(BASE_CONFIG)
    cal = frozen.calibration_from_config(base_cfg)
    settings = frozen.settings_from_config(base_cfg)
    if args.quick:
        settings = replace(settings, n_streams=20, n_calibration=20)
    if args.streams:
        settings = replace(settings, n_streams=args.streams)
    start = time.time()

    if args.partition == "test":
        rc = test_guards(args)
        print(
            f"Frozen D21 settings OK: q_rolling {rc.q_rolling:.3f}, q_anchored "
            f"{rc.q_anchored:.3f}, L {rc.periods}"
        )
        if args.check_only:
            print("Check only: stopping before any data is loaded.")
            return
        out = OUT_ROOT / "test"
        out.mkdir(parents=True, exist_ok=True)
        print("1. Test partition and predictions from the saved model ...")
        part = load_test()
        pool = part
        print("2. Scenarios from the test partition's strata ...")
        scenarios, _ = scenarios_for(pool, cal, out)
    else:
        out = OUT_ROOT / ("validation_quick" if args.quick else "validation")
        out.mkdir(parents=True, exist_ok=True)
        print("1. Validation partition ...")
        part = load_validation()
        _, pool_idx = ex.split_validation(len(part.y), settings.seed)
        pool = part.subset(pool_idx)
        print("2. Scenarios from the stream half ...")
        scenarios, base_scenarios = scenarios_for(pool, cal, out)
        print("3. Calibration on stable and harmful validation streams ...")
        rc = ra.calibrate(pool, base_scenarios, cal, settings)
        print(f"   q_rolling {rc.q_rolling:.3f}; q_anchored {rc.q_anchored:.3f}; L {rc.periods}")
        config_path = out / "strategy_a_rolling_quick.toml" if args.quick else CONFIG
        write_config(rc, args.quick, config_path)
        (out / "calibration.json").write_text(
            json.dumps(
                {"calibration": rc.to_dict(), "settings": settings.__dict__, **run_metadata()},
                indent=2,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

    print("4. Grid (same streams and label draws as the earlier runs) ...")
    results = ra.run_grid(pool, scenarios, cal, rc, settings)
    print("5. Real windows in time order ...")
    natural = ra.run_natural(part, cal, rc, settings, seed=settings.seed)
    report(results, natural, rc, args.partition, settings, out, args.quick)
    info = {
        "partition": args.partition,
        "streams_per_scenario": settings.n_streams,
        "minutes": round((time.time() - start) / 60, 1),
        "base_config_sha256": frozen.config_hash(BASE_CONFIG),
        **run_metadata(),
    }
    if args.partition == "test":
        info["config_sha256"] = frozen.config_hash(CONFIG)
    (out / "run.json").write_text(json.dumps(info, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nDone in {info['minutes']} minutes. Outputs in {out}")
    if args.partition == "validation" and not args.quick:
        print(f"Calibrated settings written to {CONFIG}: commit it before the test run.")


if __name__ == "__main__":
    main()
