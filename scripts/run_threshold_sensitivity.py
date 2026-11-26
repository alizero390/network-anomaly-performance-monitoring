"""Sensitivity of Strategy B to its alarm threshold (D23, part 2; planned in D9).

Usage (repository root, virtual environment active, raw data available):

    python scripts/run_threshold_sensitivity.py --partition validation --quick   # minutes
    python scripts/run_threshold_sensitivity.py --partition validation
    python scripts/run_threshold_sensitivity.py --partition test --check-only
    python scripts/run_threshold_sensitivity.py --partition test --confirm-committed

The alarm drop of D9 (0.05 below the reference in two consecutive eligible cohorts) is
replaced by 0.03 and by 0.10; 0.05 is run again as the check that the earlier results are
reproduced. Everything else comes unchanged from configs/strategies.toml: nothing is
calibrated or chosen here, so the threshold of the thesis stays 0.05 whatever this shows.

Only the label-based strategies depend on the drop and are run: B (calibrated F1),
B_F1 (plain F1) and B_ipw. Same scenarios, streams and label draws as the D14 runs.

Expected (D23): a lower drop detects earlier but raises false alerts on stable and
harmless streams, most of all with 20% labels; 0.10 sits at the size of the harmful
changes themselves (ground truth: a fall of at least 0.10 in expected calibrated F1),
so detection falls and delays grow.

Outputs in results/threshold_sensitivity/<partition>/ (commit them):
    stream_results.csv.gz  one row per drop, scenario, stream, condition and strategy
    summary.csv            per drop, scenario, condition and strategy
    overview.csv           random-label conditions pooled
    natural.csv            alarms on the real windows in time order, per drop
    run.json, summary.md
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
from nadmon import scenarios as sc
from nadmon.config import PROJECT_DIR, load_paths
from nadmon.provenance import run_metadata

RESULTS = PROJECT_DIR / "results"
CONFIG = PROJECT_DIR / "configs" / "strategies.toml"
VALIDATION_CALIBRATION = RESULTS / "strategies" / "validation" / "calibration.json"
EARLIER = RESULTS / "strategies"
OUT_ROOT = RESULTS / "threshold_sensitivity"
DROPS = (0.03, 0.05, 0.10)
STRATEGIES = ("B", "B_F1", "B_ipw")
CHECK_COLS = ["detected", "detection_delay", "false_alerts", "alarms"]


def guards(args) -> dict:
    cfg = frozen.read_config(CONFIG)
    problems = frozen.check_against_validation(cfg, VALIDATION_CALIBRATION)
    if problems:
        raise SystemExit(
            "configs/strategies.toml is not the final config:\n- " + "\n- ".join(problems)
        )
    if args.partition != "test":
        return cfg
    if args.quick:
        raise SystemExit("--quick is for validation only.")
    if not (OUT_ROOT / "validation" / "run.json").is_file():
        raise SystemExit("Run the full validation sensitivity first (and commit it).")
    committed = frozen.committed_unchanged(CONFIG, PROJECT_DIR)
    if committed is False:
        raise SystemExit("configs/strategies.toml has uncommitted changes: not allowed.")
    if committed is None and not args.confirm_committed and not args.check_only:
        raise SystemExit(
            "git is not available here, so the commit cannot be checked. Commit D23 and the\n"
            "validation results in GitHub Desktop, then run again with --confirm-committed."
        )
    if (OUT_ROOT / "test" / "run.json").is_file():
        raise SystemExit("A test sensitivity run already exists: the test partition is used once.")
    return cfg


def load(partition: str) -> ex.Partition:
    paths = load_paths()
    X, y, category = february.load_frames(paths, partition)
    if partition == "validation":
        pred = pd.read_csv(RESULTS / "validation_predictions.csv")
        if len(pred) != len(y) or (pred["TrueLabel"].to_numpy() != y).any():
            raise SystemExit("validation_predictions.csv does not line up with the raw data.")
        p = pred["Prediction"].to_numpy(dtype=int)
    else:
        path = EARLIER / "test" / "test_predictions.csv"
        pred = pd.read_csv(path) if path.is_file() else None
        if pred is not None and len(pred) == len(y) and (pred["TrueLabel"].to_numpy() == y).all():
            p = pred["Prediction"].to_numpy(dtype=int)
        else:
            model = joblib.load(paths.models_dir / "random_forest_baseline.joblib")
            p = model.predict(X).astype(int)
    part = february.partition(X, y, category, p)
    part.features = None  # Strategy A is not run: free the memory
    return part


def scenarios_for(pool: ex.Partition, cal: ex.Calibration, out) -> list[sc.Scenario]:
    """The D14 scenario set, built exactly as in the earlier runs."""
    rates = sc.stratum_rates(pool.strata, pool.y, pool.p)
    base = sc.standard_scenarios(rates, cal.pi0)
    base_ok = set(sc.scenario_table(base, rates, cal.pi0).query("usable")["scenario"])
    all_scen = base + sc.harder_variants([x for x in base if x.name in base_ok])
    table = sc.scenario_table(all_scen, rates, cal.pi0)
    table.to_csv(out / "scenarios.csv", index=False, lineterminator="\n")
    usable = set(table.loc[table["usable"], "scenario"])
    return [x for x in all_scen if x.name in usable]


def reproduced(results: pd.DataFrame, partition: str) -> str:
    """Compare the drop-0.05 rows with the committed D14 results."""
    path = EARLIER / partition / "stream_results.csv.gz"
    if not path.is_file():
        return f"not checked ({path.name} missing)"
    old = pd.read_csv(path)
    key = ["scenario", "stream", "condition", "strategy"]
    old = old[old["strategy"].isin(STRATEGIES)][key + CHECK_COLS]
    new = results[np.isclose(results["drop"], 0.05)][key + CHECK_COLS]
    m = new.merge(old, on=key, suffixes=("", "_old"))
    if len(m) == 0:
        return "not checked (no common streams)"
    same = np.ones(len(m), dtype=bool)
    for c in CHECK_COLS:
        a, b = m[c].to_numpy(dtype=float), m[c + "_old"].to_numpy(dtype=float)
        same &= (a == b) | (np.isnan(a) & np.isnan(b))
    if same.all():
        return f"identical ({len(m)} rows)"
    diff = m[~same]
    by = diff.groupby(["strategy", "condition"]).size().to_dict()
    return f"DIFFERENT in {len(diff)} of {len(m)} rows: {by}"


def pct(v) -> str:
    return "" if pd.isna(v) else f"{100 * v:.1f}%"


def write_summary(overview: pd.DataFrame, natural: pd.DataFrame, info: dict, out) -> None:
    lines = [
        f"# Strategy B alarm-threshold sensitivity ({info['partition']}, D23)",
        "",
        f"Drops {', '.join(str(d) for d in DROPS)}; everything else from "
        "configs/strategies.toml. Random-label conditions pooled (9 conditions x "
        f"{info['streams_per_scenario']} streams per scenario). Drop 0.05 reproduces "
        f"the D14 run: {info['reproduced']}.",
        "",
        "| Strategy | Drop | Scenario | Detection | False alerts | Median delay |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for r in overview.itertuples(index=False):
        lines.append(
            f"| {r.strategy} | {r.drop} | {r.scenario} | {pct(r.event_recall)} | "
            f"{pct(r.false_alert_rate)} | {'' if pd.isna(r.median_delay) else r.median_delay} |"
        )
    lines += [
        "",
        "## Real windows in time order",
        "",
        "| Strategy | Drop | Condition | Alarm windows |",
        "|---|---:|---|---|",
    ]
    for r in natural.itertuples(index=False):
        lines.append(f"| {r.strategy} | {r.drop} | {r.condition} | {r.alarm_windows} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", choices=("validation", "test"), required=True)
    parser.add_argument("--quick", action="store_true", help="validation, 20 streams")
    parser.add_argument("--streams", type=int, default=None)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--confirm-committed", action="store_true")
    args = parser.parse_args()

    cfg = guards(args)
    cal = frozen.calibration_from_config(cfg)
    settings = frozen.settings_from_config(cfg)
    n_streams = args.streams or (20 if args.quick else settings.n_streams)
    settings = replace(settings, n_streams=n_streams)
    print(
        f"Frozen settings OK: n_min {cal.n_min}, reference calibrated F1 "
        f"{cal.reference_f1_calibrated:.4f}, drops {DROPS}, {n_streams} streams"
    )
    if args.check_only:
        print("Check only: stopping before any data is loaded.")
        return

    start = time.time()
    name = "validation_quick" if args.quick else args.partition
    out = OUT_ROOT / name
    out.mkdir(parents=True, exist_ok=True)

    print(f"1. {args.partition} partition ...")
    part = load(args.partition)
    if args.partition == "validation":
        _, pool_idx = ex.split_validation(len(part.y), settings.seed)
        pool = part.subset(pool_idx)
    else:
        pool = part
    print(f"   {len(part.y):,} records; attack share {part.y.mean():.3f}")

    print("2. Scenarios (as in the D14 run) ...")
    scenarios = scenarios_for(pool, cal, out)
    print("   " + ", ".join(x.name for x in scenarios))

    tables, naturals = [], []
    for d in DROPS:
        s = replace(settings, drop=d)
        print(f"3. Drop {d}: grid ...")
        r = ex.run_grid(pool, scenarios, cal, s, ref=None, progress=False)
        r.insert(0, "drop", d)
        tables.append(r)
        nat = ex.run_natural(part, cal, s, None, seed=settings.seed)
        nat.insert(0, "drop", d)
        naturals.append(nat)
    results = pd.concat(tables, ignore_index=True)
    natural = pd.concat(naturals, ignore_index=True)
    results.to_csv(out / "stream_results.csv.gz", index=False, lineterminator="\n")
    natural.to_csv(out / "natural.csv", index=False, lineterminator="\n")

    summary = ev.summarise(results, ["drop", "scenario", "condition", "strategy"])
    summary.to_csv(out / "summary.csv", index=False, lineterminator="\n")
    rand = results[~results["condition"].str.contains("alert_first")]
    overview = ev.summarise(rand, ["strategy", "drop", "scenario"])
    overview.to_csv(out / "overview.csv", index=False, lineterminator="\n")

    check = reproduced(results, args.partition) if not args.quick else "not checked (quick)"
    info = {
        "partition": args.partition,
        "quick": args.quick,
        "drops": list(DROPS),
        "streams_per_scenario": n_streams,
        "config_sha256": frozen.config_hash(CONFIG),
        "reproduced": check,
        "minutes": round((time.time() - start) / 60, 1),
        **run_metadata(),
    }
    (out / "run.json").write_text(json.dumps(info, indent=2, default=str) + "\n", encoding="utf-8")
    write_summary(overview, natural, info, out)

    pd.set_option("display.width", 200)
    cols = ["strategy", "drop", "scenario", "event_recall", "false_alert_rate", "median_delay"]
    print("\nRandom-label conditions pooled:")
    print(overview[cols].round(3).to_string(index=False))
    af = ev.summarise(
        results[results["condition"].str.contains("alert_first")], ["strategy", "drop", "scenario"]
    )
    print("\nAlert-first labels:")
    print(af[cols].round(3).to_string(index=False))
    nat_cols = ["strategy", "drop", "condition", "alarm_windows"]
    print("\nReal windows, d0_p100 and d5_p20:")
    print(
        natural[natural["condition"].isin(["d0_p100", "d5_p20"])][nat_cols].to_string(index=False)
    )
    print(f"\nDrop 0.05 against the D14 run: {check}")
    print(f"Done in {info['minutes']} minutes. Outputs in {out}")


if __name__ == "__main__":
    main()
