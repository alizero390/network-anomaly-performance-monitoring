"""Figures 2 and 3 of Paper 2 (label-bias study) from the committed results.

Usage (repository root, virtual environment active; no raw data needed):

    python scripts/plot_label_bias.py                    # feb_rf, validation and test
    python scripts/plot_label_bias.py --run feb_hgb

Figure 2: heatmaps of false alarms (stable and harmless streams) and detection (harmful
streams) over p_alert x p_normal, one column per rule (B, B_ipw, B_ipw_eff, B_ipw_ess).
Figure 3: false alarms and detection against p_normal at p_alert = 0.9, with 95% Wilson
intervals and the audit-rate bound m_min / (normal records per window x max_span).

Outputs in results/label_bias/figures/: fig2_<run>_<partition>.png/.pdf,
fig3_<run>_<partition>.png/.pdf, fig3_<run>_<partition>.csv (the plotted values).
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from nadmon import evaluation as ev  # noqa: E402
from nadmon import frozen  # noqa: E402
from nadmon import label_bias as lbs  # noqa: E402
from nadmon.config import PROJECT_DIR  # noqa: E402

RESULTS = PROJECT_DIR / "results" / "label_bias"
CONFIG = PROJECT_DIR / "configs" / "strategies.toml"
RULES = ("B", "B_ipw", "B_ipw_eff", "B_ipw_ess")
NAMES = {
    "B": "B (no weights)",
    "B_ipw": "B_ipw (raw counts)",
    "B_ipw_eff": "B_ipw_eff (weighted counts)",
    "B_ipw_ess": "B_ipw_ess (effective size)",
}
# Reference palette (dataviz skill): neutral for the uncorrected rule, then slots 1-3.
COLORS = {"B": "#8a8984", "B_ipw": "#2a78d6", "B_ipw_eff": "#eb6834", "B_ipw_ess": "#1baf7a"}
INK, QUIET, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": QUIET,
        "axes.labelcolor": INK,
        "xtick.color": QUIET,
        "ytick.color": QUIET,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def results_dir(run: str, partition: str):
    return RESULTS / partition if run == "feb_rf" else RESULTS / run / partition


def fig2(table: pd.DataFrame, title: str, path) -> None:
    pas = sorted(lbs.P_ALERT_GRID, reverse=True)
    pns = sorted(lbs.P_NORMAL_GRID, reverse=True)
    t = table[(table["weights"] == "correct") & (table["policy"] == "alert_first")]
    # Sequential, one hue per measure: orange for false alarms (high = bad), blue for
    # detection (high = good).
    rows = (
        ("false_alert_rate_stable_or_harmless", "False alarms\n(stable, harmless)", "Oranges"),
        ("detection_rate_harmful", "Detection\n(harmful)", "Blues"),
    )
    fig, axes = plt.subplots(2, 4, figsize=(10, 4.6), sharex=True, sharey=True)
    for i, (col, label, cmap) in enumerate(rows):
        for j, rule in enumerate(RULES):
            ax = axes[i, j]
            sub = t[t["strategy"] == rule].set_index(["p_alert", "p_normal"])[col]
            grid = np.array([[sub.get((pa, pn), np.nan) for pn in pns] for pa in pas])
            ax.imshow(grid, cmap=cmap, vmin=0, vmax=1, aspect="auto")
            for a in range(len(pas)):
                for b in range(len(pns)):
                    v = grid[a, b]
                    if np.isfinite(v):
                        ax.text(
                            b,
                            a,
                            f"{v:.0%}",
                            ha="center",
                            va="center",
                            fontsize=7.5,
                            color="white" if v > 0.6 else INK,
                        )
            ax.set_xticks(range(len(pns)), [f"{pn:.0%}" for pn in pns])
            ax.set_yticks(range(len(pas)), [f"{pa:.0%}" for pa in pas])
            for s in ax.spines.values():
                s.set_visible(False)
            ax.tick_params(length=0)
            if i == 0:
                ax.set_title(NAMES[rule], fontsize=9, color=INK)
            if j == 0:
                ax.set_ylabel(f"{label}\n\nalerts labelled")
            if i == 1:
                ax.set_xlabel("normal traffic labelled")
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=INK, fontweight="bold")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(path.with_suffix(f".{ext}"), dpi=200)
    plt.close(fig)


def fig3_data(streams: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cond in lbs.policy_conditions():
        info = lbs.parse_condition(cond.name)
        if info["p_alert"] != 0.9 or info["weights"] != "correct":
            continue
        g = streams[streams["condition"] == cond.name]
        for rule in RULES:
            r = g[g["strategy"] == rule]
            harmless, harmful = r[~r["harmful"]], r[r["harmful"]]
            fa, fa_lo, fa_hi = ev.wilson(int(harmless["any_false_alert"].sum()), len(harmless))
            dt, dt_lo, dt_hi = ev.wilson(int(harmful["detected"].sum()), len(harmful))
            rows.append(
                {
                    "p_normal": info["p_normal"],
                    "strategy": rule,
                    "false_alarms": fa,
                    "false_alarms_low": fa_lo,
                    "false_alarms_high": fa_hi,
                    "streams_harmless": len(harmless),
                    "detection": dt,
                    "detection_low": dt_lo,
                    "detection_high": dt_hi,
                    "streams_harmful": len(harmful),
                }
            )
    return pd.DataFrame(rows).sort_values(["strategy", "p_normal"])


def fig3(data: pd.DataFrame, bound: float, title: str, path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharex=True)
    panels = (
        ("false_alarms", "Stable or harmless streams with a false alarm"),
        ("detection", "Harmful streams detected"),
    )
    for ax, (col, label) in zip(axes, panels, strict=True):
        for rule in RULES:
            d = data[data["strategy"] == rule]
            c = COLORS[rule]
            ax.fill_between(
                d["p_normal"], d[f"{col}_low"], d[f"{col}_high"], color=c, alpha=0.15, linewidth=0
            )
            ax.plot(
                d["p_normal"],
                d[col],
                color=c,
                linewidth=2,
                marker="o",
                markersize=4,
                label=NAMES[rule],
                linestyle="--" if rule == "B" else "-",
            )
        ax.axvline(bound, color=QUIET, linewidth=1, linestyle=":")
        ax.text(
            bound / 1.05,
            0.62,
            f"audit bound {bound:.1%}",
            color=QUIET,
            fontsize=8,
            rotation=90,
            va="center",
            ha="right",
        )
        ax.set_xscale("log")
        ticks = sorted(lbs.P_NORMAL_GRID)
        ax.set_xticks(ticks, [f"{t:.0%}" for t in ticks])
        ax.minorticks_off()
        ax.set_ylim(-0.03, 1.03)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_title(label, fontsize=9.5, color=INK, loc="left")
        ax.set_xlabel("normal traffic labelled (alerts labelled: 90%)")
    axes[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=INK, fontweight="bold")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(path.with_suffix(f".{ext}"), dpi=200)
    plt.close(fig)


def audit_bound() -> float:
    """m_min / (normal records per window at the reference share x max_span)."""
    cfg = frozen.read_config(CONFIG)
    b, s = cfg["strategy_b"], cfg["streams"]
    attack_share = float(cfg["reference"]["attack_share"])
    normals = int(s["window_size"]) * (1 - attack_share)
    return float(b["m_min"]) / (normals * int(b["max_span"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", choices=lbs.MODELS, default="feb_rf")
    args = parser.parse_args()
    out = RESULTS / "figures"
    out.mkdir(parents=True, exist_ok=True)
    for partition in ("validation", "test"):
        folder = results_dir(args.run, partition)
        if not (folder / "policy_table.csv").is_file():
            print(f"skipping {partition}: no results in {folder}")
            continue
        table = pd.read_csv(folder / "policy_table.csv")
        name = f"{args.run}_{partition}"
        fig2(
            table,
            f"Alert-first labelling, {args.run}, UNSW-NB15 {partition}: false alarms and detection",
            out / f"fig2_{name}",
        )
        streams = pd.read_csv(folder / "stream_results.csv.gz")
        data = fig3_data(streams)
        data.to_csv(out / f"fig3_{name}.csv", index=False, lineterminator="\n")
        bound = audit_bound()
        fig3(
            data,
            bound,
            f"Labelling less normal traffic, {args.run}, UNSW-NB15 {partition}",
            out / f"fig3_{name}",
        )
        print(f"{name}: figures written (audit bound {bound:.1%})")
    print(f"Outputs in {out}")


if __name__ == "__main__":
    main()
