"""Strategy A with a minimum effect size (decision D22): validation calibration and test run.

Usage (repository root, virtual environment active, raw data available):

    python scripts/run_strategy_a_floor.py --partition validation --quick   # first check
    python scripts/run_strategy_a_floor.py --partition validation           # calibrate + run
    (commit configs/strategy_a_floor.toml and results/strategy_a_floor/validation/)
    python scripts/run_strategy_a_floor.py --partition test --check-only
    python scripts/run_strategy_a_floor.py --partition test --confirm-committed

D21's frozen settings (configs/strategy_a_rolling.toml) and configs/strategies.toml are
used unchanged. Validation calibrates epsilon on the real validation windows in time
order and q on 100 stable validation streams (D22); both are written to
configs/strategy_a_floor.toml. The test run (once) calibrates nothing.

Outputs in results/strategy_a_floor/<partition>[_quick]/: calibration.json (validation),
run.json, stream_results.csv.gz (with the D21 rows A_rolling and C_active_rolling for
comparison), summary.csv, summary.md, paired_*.csv, natural.csv, natural_windows.csv.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_strategy_a_rolling as d21  # noqa: E402
from nadmon import effect_floor as ef  # noqa: E402
from nadmon import evaluation as ev  # noqa: E402
from nadmon import experiment as ex  # noqa: E402
from nadmon import frozen  # noqa: E402
from nadmon.config import PROJECT_DIR  # noqa: E402
from nadmon.provenance import run_metadata  # noqa: E402

RESULTS = PROJECT_DIR / "results"
BASE_CONFIG = PROJECT_DIR / "configs" / "strategies.toml"
D21_CONFIG = PROJECT_DIR / "configs" / "strategy_a_rolling.toml"
CONFIG = PROJECT_DIR / "configs" / "strategy_a_floor.toml"
OUT_ROOT = RESULTS / "strategy_a_floor"
D21_RESULTS = RESULTS / "strategy_a_rolling"


def write_config(fc: ef.FloorCalibration, quick: bool, path) -> None:
    lines = [
        "# Strategy A with a minimum effect size (RESEARCH_DECISIONS.md D22), calibrated on",
        "# February validation by scripts/run_strategy_a_floor.py. Commit it before the test",
        "# run; the test run must use these values unchanged.",
        f'base_config_sha256 = "{frozen.config_hash(BASE_CONFIG)}"',
        f'd21_config_sha256 = "{frozen.config_hash(D21_CONFIG)}"',
        f"quick_run = {str(quick).lower()}",
        "",
        "[a_floor]",
        f"epsilon = {fc.epsilon}",
        f"q = {fc.q}",
        f"lookback = {fc.lookback}",
        f"gap = {fc.gap}",
        "",
        "[c_active_floor.association_period]",
        *[f'"{d}" = {L}' for d, L in sorted(fc.periods.items())],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_config(cfg: dict) -> ef.FloorCalibration:
    a = cfg["a_floor"]
    return ef.FloorCalibration(
        epsilon=float(a["epsilon"]),
        q=float(a["q"]),
        lookback=int(a["lookback"]),
        gap=int(a["gap"]),
        periods={int(k): int(v) for k, v in cfg["c_active_floor"]["association_period"].items()},
    )


def test_guards(args) -> ef.FloorCalibration:
    if not CONFIG.is_file():
        raise SystemExit(f"{CONFIG} not found: run --partition validation (full) first.")
    cfg = frozen.read_config(CONFIG)
    if cfg.get("quick_run", True):
        raise SystemExit("configs/strategy_a_floor.toml comes from a quick run.")
    if cfg.get("base_config_sha256") != frozen.config_hash(BASE_CONFIG):
        raise SystemExit("configs/strategies.toml changed since the D22 calibration.")
    if cfg.get("d21_config_sha256") != frozen.config_hash(D21_CONFIG):
        raise SystemExit("configs/strategy_a_rolling.toml changed since the D22 calibration.")
    fc = read_config(cfg)
    saved = json.loads((OUT_ROOT / "validation" / "calibration.json").read_text(encoding="utf-8"))
    saved = saved["calibration"]
    if not (np.isclose(saved["epsilon"], fc.epsilon) and np.isclose(saved["q"], fc.q)):
        raise SystemExit("The config differs from results/strategy_a_floor/validation.")
    committed = frozen.committed_unchanged(CONFIG, PROJECT_DIR)
    if committed is False:
        raise SystemExit("configs/strategy_a_floor.toml has uncommitted changes. Commit it.")
    if committed is None and not args.confirm_committed and not args.check_only:
        raise SystemExit(
            "git is not available here. Commit configs/strategy_a_floor.toml in GitHub "
            "Desktop, then run again with --confirm-committed."
        )
    if (OUT_ROOT / "test" / "run.json").is_file():
        raise SystemExit("A D22 test run already exists: the test partition is used once.")
    return fc


def d21_rows(partition: str, n_streams: int) -> pd.DataFrame:
    path = D21_RESULTS / partition / "stream_results.csv.gz"
    if not path.is_file():
        return pd.DataFrame()
    old = pd.read_csv(path)
    keep = old["strategy"].isin(["A_rolling", "C_active_rolling"]) & (old["stream"] < n_streams)
    return old[keep]


def summary_markdown(summary, natural, windows, fc, partition, quick) -> str:
    def pct(v):
        return "–" if pd.isna(v) else f"{v:.0%}"

    def num(v):
        return "–" if pd.isna(v) else f"{v:g}"

    shares = ", ".join(f"{k:g}: {v:.0%}" for k, v in fc.real_window_share.items())
    lines = [
        f"# Strategy A with a minimum effect size (D22): February {partition}"
        + (" (quick run)" if quick else ""),
        "",
        "Generated by `scripts/run_strategy_a_floor.py`. A feature counts as changed if its "
        "Benjamini-Hochberg p-value is at most 0.01 and its effect size (Kolmogorov-Smirnov "
        "statistic or total variation distance) is at least epsilon. A_rolling and "
        "C_active_rolling are the D21 results on the same streams.",
        "",
        f"Settings: epsilon = {fc.epsilon:g}, q = {fc.q:.3f}, rolling reference windows "
        f"w-{fc.gap + fc.lookback - 1}..w-{fc.gap}, L = {fc.periods}.",
        "",
    ]
    if shares:
        lines += [f"Real validation windows flagged by epsilon (calibration): {shares}.", ""]
    lines += [
        "| Scenario | Condition | Strategy | Streams | Event recall | False-alert rate | "
        "Median delay |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {r.scenario} | {r.condition} | {r.strategy} | {r.streams} | "
            f"{pct(r.event_recall)} | {pct(r.false_alert_rate)} | {num(r.median_delay)} |"
        )
    judged = windows[windows["judged"]]
    lines += [
        "",
        f"## Real {partition} windows in time order",
        "",
        f"{int(judged['flagged'].sum())} of {len(judged)} judged windows flagged "
        f"({judged['flagged'].mean():.0%}); median changed proportion "
        f"{judged['changed_proportion_floor'].median():.2f} with the floor, "
        f"{judged['changed_proportion_no_floor'].median():.2f} without.",
        "",
        "| Strategy | Condition | Alarms | Alarm windows (1-based) |",
        "|---|---|---:|---|",
    ]
    for r in natural.itertuples(index=False):
        lines.append(f"| {r.strategy} | {r.condition} | {r.alarms} | {r.alarm_windows} |")
    return "\n".join(lines) + "\n"


def report(results, natural, windows, fc, partition, settings, out, quick) -> None:
    combined = pd.concat([results, d21_rows(partition, settings.n_streams)], ignore_index=True)
    combined.to_csv(out / "stream_results.csv.gz", index=False, lineterminator="\n")
    summary = ev.summarise(combined, ["scenario", "condition", "strategy"])
    summary.to_csv(out / "summary.csv", index=False, lineterminator="\n")
    for a, b in [("C_active_floor", "B"), ("A_floor", "A_rolling")]:
        if {a, b} <= set(combined["strategy"]):
            ev.paired_comparison(combined, a, b).to_csv(
                out / f"paired_{a}_vs_{b}.csv", index=False, lineterminator="\n"
            )
    natural.to_csv(out / "natural.csv", index=False, lineterminator="\n")
    windows.to_csv(out / "natural_windows.csv", index=False, lineterminator="\n")
    (out / "summary.md").write_text(
        summary_markdown(summary, natural, windows, fc, partition, quick), encoding="utf-8"
    )
    random = combined[~combined["condition"].str.contains("alert_first")]
    overview = ev.summarise(random, ["scenario", "strategy"])
    cols = ["scenario", "strategy", "event_recall", "false_alert_rate", "median_delay"]
    print("\nOverview (random-label conditions pooled; A variants on inputs):")
    print(overview[cols].round(3).to_string(index=False))
    judged = windows[windows["judged"]]
    print(
        f"\nReal windows in time order: {int(judged['flagged'].sum())} of {len(judged)} "
        f"judged windows flagged ({judged['flagged'].mean():.0%})."
    )
    print(natural[["strategy", "condition", "alarms", "alarm_windows"]].to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", choices=["validation", "test"], required=True)
    parser.add_argument("--quick", action="store_true", help="validation: 20 streams")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--confirm-committed", action="store_true")
    args = parser.parse_args()
    if args.partition == "test" and args.quick:
        raise SystemExit("--quick is for validation only.")

    base_cfg = frozen.read_config(BASE_CONFIG)
    cal = frozen.calibration_from_config(base_cfg)
    settings = frozen.settings_from_config(base_cfg)
    if args.quick:
        settings = replace(settings, n_streams=20, n_calibration=20)
    if not D21_CONFIG.is_file():
        raise SystemExit(f"{D21_CONFIG} not found: D22 builds on the frozen D21 settings.")
    rolling = d21.read_config(frozen.read_config(D21_CONFIG))
    start = time.time()

    if args.partition == "test":
        fc = test_guards(args)
        print(f"Frozen D22 settings OK: epsilon {fc.epsilon:g}, q {fc.q:.3f}, L {fc.periods}")
        if args.check_only:
            print("Check only: stopping before any data is loaded.")
            return
        out = OUT_ROOT / "test"
        out.mkdir(parents=True, exist_ok=True)
        print("1. Test partition and predictions from the saved model ...")
        part = pool = d21.load_test()
        print("2. Scenarios from the test partition's strata ...")
        scenarios, _ = d21.scenarios_for(pool, cal, out)
    else:
        out = OUT_ROOT / ("validation_quick" if args.quick else "validation")
        out.mkdir(parents=True, exist_ok=True)
        print("1. Validation partition ...")
        part = d21.load_validation()
        _, pool_idx = ex.split_validation(len(part.y), settings.seed)
        pool = part.subset(pool_idx)
        print("2. Scenarios from the stream half ...")
        scenarios, base_scenarios = d21.scenarios_for(pool, cal, out)
        print("3. Calibration: epsilon on real windows, q on stable streams ...")
        fc = ef.calibrate(part, pool, base_scenarios, settings, rolling)
        print(f"   epsilon {fc.epsilon:g}; q {fc.q:.3f}")
        write_config(fc, args.quick, out / "strategy_a_floor_quick.toml" if args.quick else CONFIG)
        (out / "calibration.json").write_text(
            json.dumps(
                {"calibration": fc.to_dict(), "settings": settings.__dict__, **run_metadata()},
                indent=2,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

    print("4. Grid (same streams and label draws as the earlier runs) ...")
    results = ef.run_grid(pool, scenarios, cal, fc, settings)
    print("5. Real windows in time order ...")
    natural, windows = ef.run_natural(part, cal, fc, settings, seed=settings.seed)
    report(results, natural, windows, fc, args.partition, settings, out, args.quick)
    info = {
        "partition": args.partition,
        "streams_per_scenario": settings.n_streams,
        "minutes": round((time.time() - start) / 60, 1),
        "base_config_sha256": frozen.config_hash(BASE_CONFIG),
        "d21_config_sha256": frozen.config_hash(D21_CONFIG),
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
