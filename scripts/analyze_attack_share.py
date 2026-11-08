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
LATE_PERIOD_START = 50  # first window of the late low-attack period

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


EASY_CATEGORY = "Generic"


def export_category_tables(pred: pd.DataFrame, n_windows: int) -> None:
    """Write per-category tables from results/validation_categories.csv (local only)."""
    path = RESULTS / "validation_categories.csv"
    if not path.is_file():
        print("validation_categories.csv not found; using committed category tables if present.")
        return

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
    per_cat.to_csv(OUT / "category_recall.csv", lineterminator="\n")

    attacks["window"] = attacks.index // WINDOW_SIZE + 1
    attacks = attacks[attacks["window"] <= n_windows]
    mix = pd.crosstab(attacks["window"], attacks["AttackCategory"], normalize="index")
    mix.to_csv(OUT / "category_mix_by_window.csv", lineterminator="\n")

    counts = (
        attacks.groupby(["window", "AttackCategory"])
        .agg(records=("Detected", "size"), detected=("Detected", "sum"))
        .reset_index()
    )
    counts.to_csv(OUT / "category_window_counts.csv", index=False, lineterminator="\n")


def categories(windows: pd.DataFrame) -> dict | None:
    """Category analysis from the committed category tables."""
    recall_path = OUT / "category_recall.csv"
    mix_path = OUT / "category_mix_by_window.csv"
    if not (recall_path.is_file() and mix_path.is_file()):
        print("Category tables not found; skipping category analysis.")
        return None

    per_cat = pd.read_csv(recall_path, index_col="AttackCategory")
    mix = pd.read_csv(mix_path, index_col="window")
    w = windows.set_index("window").loc[mix.index]
    attacks_per_window = w["tp"] + w["fn"]
    counts = mix.mul(attacks_per_window, axis=0)  # attacks per category per window

    # Recall each window would have if every category kept its pooled recall,
    # so window differences come only from the category mix.
    expected = mix.mul(per_cat["recall"], axis=1).sum(axis=1)

    easy = counts[EASY_CATEGORY]
    other = counts.drop(columns=EASY_CATEGORY).sum(axis=1)
    low = w["attack_share"] < LOW_SHARE
    misses = per_cat["records"] * (1 - per_cat["recall"])
    others = per_cat.drop(index=EASY_CATEGORY)

    summary = {
        "categories": per_cat.reset_index().to_dict(orient="records"),
        "r2_recall_explained_by_category_mix": ash.r_squared(w["recall"], expected),
        "spearman_expected_vs_observed_recall": float(
            w["recall"].corr(expected, method="spearman")
        ),
        "easy_category": EASY_CATEGORY,
        "easy_share_of_attacks": float(
            per_cat.loc[EASY_CATEGORY, "records"] / per_cat["records"].sum()
        ),
        "recall_excluding_easy": float(
            (others["records"] * others["recall"]).sum() / others["records"].sum()
        ),
        "share_of_misses": {k: float(v) for k, v in (misses / misses.sum()).items()},
        "spearman_with_attack_share": {
            "easy_count": float(easy.corr(w["attack_share"], method="spearman")),
            "other_attack_count": float(other.corr(w["attack_share"], method="spearman")),
        },
        "low_vs_high_share": {
            "easy_per_window": [float(easy[low].mean()), float(easy[~low].mean())],
            "other_attacks_per_window": [float(other[low].mean()), float(other[~low].mean())],
            "mix_percent_low": (mix[low].mean() * 100).round(2).to_dict(),
            "mix_percent_high": (mix[~low].mean() * 100).round(2).to_dict(),
            "expected_recall": [float(expected[low].mean()), float(expected[~low].mean())],
        },
        "spearman_fpr_vs_fuzzers_share": float(w["fpr"].corr(mix["Fuzzers"], method="spearman")),
    }

    within = OUT / "category_window_counts.csv"
    if within.is_file():
        cw = pd.read_csv(within)
        cw = cw.merge(w[["attack_share"]], left_on="window", right_index=True)
        cw["low"] = cw["attack_share"] < LOW_SHARE
        grouped = cw.groupby(["AttackCategory", "low"])[["records", "detected"]].sum()
        grouped["recall"] = grouped["detected"] / grouped["records"]
        summary["within_category_recall_low_vs_high"] = {
            cat: {
                "low": float(grouped.loc[(cat, True), "recall"])
                if (cat, True) in grouped.index
                else None,
                "high": float(grouped.loc[(cat, False), "recall"])
                if (cat, False) in grouped.index
                else None,
            }
            for cat in per_cat.index
        }

        # Split the pooled recall gap between low- and high-share windows into
        # (a) a different category mix and (b) lower recall within categories.
        low_g, high_g = grouped.xs(True, level="low"), grouped.xs(False, level="low")
        mix_low = low_g["records"] / low_g["records"].sum()
        mix_high = high_g["records"] / high_g["records"].sum()
        rec_low = low_g["recall"]
        rec_high = high_g["recall"].reindex(rec_low.index)
        pooled_low = float((mix_low * rec_low).sum())
        pooled_high = float((mix_high * high_g["recall"]).sum())
        low_mix_high_recall = float((mix_low * rec_high).sum())
        within_by_cat = (mix_low * (rec_high - rec_low)).dropna()
        summary["recall_gap_decomposition"] = {
            "pooled_recall_low": pooled_low,
            "pooled_recall_high": pooled_high,
            "gap": pooled_high - pooled_low,
            "from_category_mix": pooled_high - low_mix_high_recall,
            "from_within_category": low_mix_high_recall - pooled_low,
            "within_category_by_category": within_by_cat.to_dict(),
        }
        fuzzers = cw[cw["AttackCategory"] == "Fuzzers"].copy()
        fuzzers["period"] = pd.cut(
            fuzzers["window"],
            [0, REFERENCE_WINDOWS, LATE_PERIOD_START - 1, fuzzers["window"].max()],
            labels=["start", "middle", "end"],
        )
        fp = fuzzers.groupby("period", observed=True)[["records", "detected"]].sum()
        summary["fuzzers_recall_by_period"] = {
            str(k): {"records": int(r.records), "recall": float(r.detected / r.records)}
            for k, r in fp.iterrows()
        }

    figure_categories(windows, counts, expected)
    return summary


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------


def figure_categories(windows: pd.DataFrame, counts: pd.DataFrame, expected: pd.Series) -> None:
    w = windows.set_index("window").loc[counts.index]
    easy = counts[EASY_CATEGORY]
    other = counts.drop(columns=EASY_CATEGORY).sum(axis=1)

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.bar(counts.index, other, color=COLORS["mcc"], width=0.8, label="All other attack categories")
    ax.bar(
        counts.index,
        easy,
        bottom=other,
        color=COLORS["f1"],
        width=0.8,
        label=f"{EASY_CATEGORY} attacks",
    )
    ax.set_xlabel("Validation window (5,000 records each)")
    ax.set_ylabel("Attack records")
    ax.set_title(f"Apart from one DoS/Exploits burst, attack volume swings are {EASY_CATEGORY}")
    ax.legend(loc="upper right")
    save(fig, "fig5_attack_categories_by_window")

    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    lo, hi = 0.6, 1.005
    ax.plot([lo, hi], [lo, hi], color=INK_2, linewidth=1, linestyle="--")
    ax.scatter(
        expected,
        w["recall"],
        s=26,
        color=COLORS["f1"],
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )
    ax.text(0.66, 0.675, "Observed = expected", color=INK_2, fontsize=8, rotation=41)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("Recall expected from category mix")
    ax.set_ylabel("Observed window recall")
    ax.set_title("Category mix predicts window recall")
    save(fig, "fig6_recall_expected_from_category_mix")


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

    export_category_tables(pred, len(windows))
    category_summary = categories(windows)

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
