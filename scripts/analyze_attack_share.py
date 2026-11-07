"""Attack-share analysis of the baseline's validation windows.

Usage:  python scripts/analyze_attack_share.py

Needs results/validation_predictions.csv (from scripts/baseline.py). If
results/validation_categories.csv exists (from
scripts/export_validation_categories.py), the attack-category analysis runs too.

Writes everything to results/attack_share/.
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nadmon import attack_share as ash
from nadmon.config import PROJECT_DIR
from nadmon.dataset import WINDOW_SIZE
from nadmon.provenance import run_metadata

RESULTS = PROJECT_DIR / "results"
OUT = RESULTS / "attack_share"
FIGURES = OUT / "figures"

SEED = 20261108
SHARES = (0.005, 0.01, 0.02, 0.05, 0.10, 0.30, 0.50)  # plus the validation share
SIM_WINDOWS = 4000  # simulated windows per attack share
STREAM_LENGTH = 20  # windows per simulated monitoring stream
DROP = 0.05  # Strategy B: drop of at least 0.05 ...
CONSECUTIVE = 2  # ... in two consecutive windows
REFERENCE_WINDOWS = 10  # candidate reference period: first 10 windows
LOW_SHARE = 0.12  # split used for the low/high attack-share comparison

METRIC_LABELS = {
    "f1": "F1",
    "mcc": "MCC",
    "balanced_accuracy": "Balanced accuracy",
    "recall": "Recall",
}

# Reference palette (light mode, categorical slots 1-4) and text inks.
COLORS = {"f1": "#2a78d6", "mcc": "#eb6834", "balanced_accuracy": "#1baf7a", "recall": "#eda100"}
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.size": 9,
            "axes.edgecolor": INK_2,
            "axes.labelcolor": INK,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "xtick.color": INK_2,
            "ytick.color": INK_2,
            "legend.frameon": False,
            "lines.linewidth": 2,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGURES / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


# ----------------------------------------------------------------------------
# 1. Observed windows
# ----------------------------------------------------------------------------


def observed_windows(pred: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    y = pred["TrueLabel"].to_numpy()
    yhat = pred["Prediction"].to_numpy()
    score = pred["AttackProbability"].to_numpy()

    share = float(y.mean())
    tpr = float(yhat[y == 1].mean())
    fpr = float(yhat[y == 0].mean())

    windows = ash.window_table(y, yhat, score, pred["Timestamp"].to_numpy(), WINDOW_SIZE)
    windows = ash.decompose_f1(windows, tpr, fpr, share)

    low = windows[windows["attack_share"] < LOW_SHARE]
    high = windows[windows["attack_share"] >= LOW_SHARE]
    cols = ["recall", "fpr", "f1", "mcc", "balanced_accuracy", "roc_auc", "average_precision"]

    # Missed attacks close to the 0.5 threshold.
    missed = (y == 1) & (yhat == 0)
    near = missed & (score >= 0.3)

    summary = {
        "pooled": {"attack_share": share, "recall": tpr, "fpr": fpr},
        "windows": len(windows),
        "spearman_with_attack_share": {
            c: float(windows[c].corr(windows["attack_share"], method="spearman")) for c in cols
        },
        "low_vs_high_share": {
            "split": LOW_SHARE,
            "n_low": len(low),
            "n_high": len(high),
            "low_mean": {c: float(low[c].mean()) for c in cols},
            "high_mean": {c: float(high[c].mean()) for c in cols},
        },
        "f1_decomposition": {
            "observed_sd": float(windows["f1"].std()),
            "share_only_sd": float(windows["f1_share_only"].std()),
            "performance_only_sd": float(windows["f1_performance_only"].std()),
            "r2_share_only": ash.r_squared(windows["f1"], windows["f1_share_only"]),
            "r2_performance_only": ash.r_squared(windows["f1"], windows["f1_performance_only"]),
        },
        "missed_attacks": {
            "total": int(missed.sum()),
            "with_score_at_least_0.3": int(near.sum()),
        },
    }
    return windows, summary


def observed_alarms(windows: pd.DataFrame) -> pd.DataFrame:
    """Strategy B alarms on the unshifted validation sequence, per metric/reference."""
    rows = []
    for metric in METRIC_LABELS:
        values = windows[metric].to_numpy()
        # (name, reference value, first monitored window index)
        references = [
            ("first_10_windows_mean", float(values[:REFERENCE_WINDOWS].mean()), REFERENCE_WINDOWS),
            ("all_validation_windows_mean", float(values.mean()), 0),
        ]
        for ref_name, ref, start in references:
            flagged = values <= ref - DROP
            run, confirmed = 0, []
            for i in range(start, len(values)):
                run = run + 1 if flagged[i] else 0
                if run >= CONSECUTIVE:
                    confirmed.append(i + 1)
            rows.append(
                {
                    "metric": metric,
                    "reference": ref_name,
                    "reference_value": ref,
                    "monitored_windows": len(values) - start,
                    "windows_below_threshold": int(flagged[start:].sum()),
                    "confirmed_alarm_windows": len(confirmed),
                    "first_alarm_window": confirmed[0] if confirmed else None,
                }
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# 2. Controlled resampling
# ----------------------------------------------------------------------------


def resampling(pred: pd.DataFrame, reference_share: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    y = pred["TrueLabel"].to_numpy()
    yhat = pred["Prediction"].to_numpy()
    shares = tuple(sorted({*SHARES, round(reference_share, 3)}))
    sim = ash.resample_at_shares(y, yhat, shares, WINDOW_SIZE, SIM_WINDOWS, SEED)

    summary = (
        sim.groupby("target_share")[list(METRIC_LABELS) + ["fpr", "precision"]]
        .quantile([0.05, 0.5, 0.95])
        .unstack()
    )
    summary.columns = [f"{m}_q{int(q * 100):02d}" for m, q in summary.columns]
    summary = summary.reset_index()

    ref_rows = sim[sim["target_share"] == round(reference_share, 3)]
    alarm_rows = []
    for share in shares:
        block = sim[sim["target_share"] == share]
        for metric in METRIC_LABELS:
            reference = float(ref_rows[metric].median())
            alarm_rows.append(
                {
                    "target_share": share,
                    "metric": metric,
                    "reference_value": reference,
                    "median_value": float(block[metric].median()),
                    "window_flag_rate": float(
                        (block[metric].to_numpy() <= reference - DROP).mean()
                    ),
                    "stream_alarm_rate": ash.alarm_rate(
                        block[metric].to_numpy(), reference, DROP, CONSECUTIVE, STREAM_LENGTH
                    ),
                }
            )
    return summary, pd.DataFrame(alarm_rows)


# ----------------------------------------------------------------------------
# 3. Attack categories (optional input)
# ----------------------------------------------------------------------------


def categories(pred: pd.DataFrame, windows: pd.DataFrame) -> dict | None:
    path = RESULTS / "validation_categories.csv"
    if not path.is_file():
        print("Category file not found; skipping category analysis.")
        return None

    cats = pd.read_csv(path)
    merged = pred.merge(cats, on="FebruarySortedIndex", how="left", validate="one_to_one")
    if (
        merged["AttackCategory"].isna().any()
        or (merged["Timestamp"].to_numpy() != merged["CategoryTimestamp"].to_numpy()).any()
        or (merged["TrueLabel"].to_numpy() != merged["CategoryLabel"].to_numpy()).any()
    ):
        raise RuntimeError("Category file does not align with the predictions file.")

    attacks = merged[merged["TrueLabel"] == 1].copy()
    attacks["Detected"] = attacks["Prediction"] == 1
    per_cat = (
        attacks.groupby("AttackCategory")
        .agg(records=("Detected", "size"), recall=("Detected", "mean"))
        .sort_values("records", ascending=False)
    )
    per_cat.to_csv(OUT / "category_recall.csv")

    attacks["window"] = attacks.index // WINDOW_SIZE + 1
    attacks = attacks[attacks["window"] <= len(windows)]
    mix = pd.crosstab(attacks["window"], attacks["AttackCategory"], normalize="index")
    mix.to_csv(OUT / "category_mix_by_window.csv")

    # Recall each window would have if each category kept its pooled recall:
    # differences are then explained purely by the category mix.
    expected = mix.mul(per_cat["recall"], axis=1).sum(axis=1)
    observed = windows.set_index("window").loc[mix.index, "recall"]
    return {
        "categories": per_cat.reset_index().to_dict(orient="records"),
        "r2_recall_explained_by_category_mix": ash.r_squared(observed, expected),
        "spearman_expected_vs_observed_recall": float(observed.corr(expected, method="spearman")),
    }


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------


def figure_f1_vs_share(windows: pd.DataFrame, pooled: dict) -> None:
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    grid = np.linspace(0.04, 0.72, 200)
    ax.plot(
        grid * 100,
        ash.f1_from_rates(pooled["recall"], pooled["fpr"], grid),
        color=INK_2,
        linewidth=1.5,
        linestyle="--",
    )
    ax.scatter(
        windows["attack_share"] * 100,
        windows["f1"],
        s=26,
        color=COLORS["f1"],
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )
    ax.annotate(
        "Expected if only the\nattack share changed",
        xy=(45, float(ash.f1_from_rates(pooled["recall"], pooled["fpr"], 0.45))),
        xytext=(40, 0.86),
        color=INK_2,
        fontsize=8,
        arrowprops={"arrowstyle": "-", "color": INK_2, "linewidth": 0.8},
    )
    ax.text(9, 0.745, "Observed windows", color=INK, fontsize=8)
    ax.set_xlabel("Attack share of window (%)")
    ax.set_ylabel("Window F1")
    ax.set_title("Low-attack windows fall far below the attack-share expectation")
    ax.set_ylim(0.7, 1.005)
    save(fig, "fig1_f1_vs_attack_share")


def figure_rates_vs_share(windows: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for ax, col, label in [
        (axes[0], "recall", "Recall (detected attacks)"),
        (axes[1], "fpr", "False positive rate"),
    ]:
        values = windows[col] * (100 if col == "fpr" else 1)
        ax.scatter(
            windows["attack_share"] * 100,
            values,
            s=26,
            color=COLORS["f1"],
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
        ax.set_xlabel("Attack share of window (%)")
        ax.set_title(label)
    axes[1].set_ylabel("%")
    fig.suptitle(
        "Detection itself is worse in low-attack windows",
        x=0.01,
        ha="left",
        fontweight="bold",
        fontsize=10,
    )
    save(fig, "fig2_recall_fpr_vs_attack_share")


def figure_resampling(summary: pd.DataFrame, reference_share: float) -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    x = summary["target_share"] * 100
    for metric, label in METRIC_LABELS.items():
        ax.fill_between(
            x,
            summary[f"{metric}_q05"],
            summary[f"{metric}_q95"],
            color=COLORS[metric],
            alpha=0.15,
            linewidth=0,
        )
        ax.plot(x, summary[f"{metric}_q50"], color=COLORS[metric], marker="o", markersize=4)
        ax.text(
            x.iloc[0] * 0.93,
            summary[f"{metric}_q50"].iloc[0],
            label,
            ha="right",
            va="center",
            fontsize=8,
            color=INK,
        )
    ax.axvline(reference_share * 100, color=INK_2, linewidth=0.8, linestyle=":")
    ax.text(reference_share * 100 * 1.05, 0.66, "Validation\nshare", fontsize=7, color=INK_2)
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50])
    ax.set_xticklabels(["0.5", "1", "2", "5", "10", "20", "50"])
    ax.set_xlim(0.09, 60)
    ax.set_xlabel("Attack share of window (%, log scale)")
    ax.set_ylabel("Metric value (median, 5-95% band)")
    ax.set_title("Same model, only the attack share varies")
    save(fig, "fig3_resampled_metrics_vs_attack_share")


def figure_timeline(windows: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.2), sharex=True)
    axes[0].plot(windows["window"], windows["f1"], color=COLORS["f1"], marker="o", markersize=3)
    axes[0].set_ylabel("Window F1")
    axes[0].set_title("Window F1 and attack share over the validation period")
    axes[1].bar(windows["window"], windows["attack_share"] * 100, color=COLORS["f1"], width=0.8)
    axes[1].set_ylabel("Attack share (%)")
    axes[1].set_xlabel("Validation window (5,000 records each)")
    save(fig, "fig4_timeline")


# ----------------------------------------------------------------------------


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    style()

    pred = pd.read_csv(RESULTS / "validation_predictions.csv")

    windows, obs = observed_windows(pred)
    windows.to_csv(OUT / "window_metrics_extended.csv", index=False, lineterminator="\n")

    alarms_observed = observed_alarms(windows)
    alarms_observed.to_csv(OUT / "alarms_on_validation.csv", index=False, lineterminator="\n")

    reference_share = obs["pooled"]["attack_share"]
    sim_summary, sim_alarms = resampling(pred, reference_share)
    sim_summary.to_csv(OUT / "resampling_quantiles.csv", index=False, lineterminator="\n")
    sim_alarms.to_csv(OUT / "resampling_alarm_rates.csv", index=False, lineterminator="\n")

    category_summary = categories(pred, windows)

    figure_f1_vs_share(windows, obs["pooled"])
    figure_rates_vs_share(windows)
    figure_resampling(sim_summary, reference_share)
    figure_timeline(windows)

    summary = {
        "observed": obs,
        "settings": {
            "window_size": WINDOW_SIZE,
            "seed": SEED,
            "simulated_windows_per_share": SIM_WINDOWS,
            "stream_length": STREAM_LENGTH,
            "drop": DROP,
            "consecutive": CONSECUTIVE,
        },
        "categories": category_summary,
        "provenance": run_metadata(),
    }
    with open(OUT / "summary.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, default=float)

    d = obs["f1_decomposition"]
    print(f"Windows: {obs['windows']}  pooled attack share {pct(reference_share)}")
    print(f"F1 variance explained by attack share alone: R2 = {d['r2_share_only']:.2f}")
    print(f"F1 variance explained by recall/FPR alone:   R2 = {d['r2_performance_only']:.2f}")
    print("\nAlarms on unshifted validation data:")
    print(alarms_observed.to_string(index=False))
    print("\nSimulated stream alarm rates (only attack share changes):")
    print(
        sim_alarms.pivot(index="target_share", columns="metric", values="stream_alarm_rate")
        .round(3)
        .to_string()
    )
    print(f"\nOutputs in {OUT}")


if __name__ == "__main__":
    main()
