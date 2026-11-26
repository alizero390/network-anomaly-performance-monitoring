"""Per-window description and cause of performance dips on a time-ordered partition.

Used to explain the alarms that Strategy B raised on the real February test windows
(results/strategies/test/natural_test.csv, windows 45-49 and 54). Every window is
described with all labels (the truth, not what a monitor saw); a window counts as
*flagged* when its calibrated F1 is at least ``drop`` below the reference. A flagged
window gets one cause, with the rules of scripts/attribute_alarms.py (Paper 1):

    too_few_attacks      fewer than n_min attacks: recall too noisy to judge
    missed_attacks       recall at least ``drop`` below the reference recall
    false_positive_burst recall fine, FPR above max(2 x reference FPR, 0.5%)
    attack_share_effect  calibrated F1 fell while recall and FPR stayed normal

The rule order decides ties. For missed attacks, the category with the most missed
records is reported.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from nadmon import strategies as st

FP_BURST_MIN = 0.005


@dataclass(frozen=True)
class References:
    pi0: float
    recall: float
    fpr: float
    f1_calibrated: float
    n_min: int
    drop: float = 0.05

    @property
    def fp_burst(self) -> float:
        return max(2 * self.fpr, FP_BURST_MIN)


def cause(attacks: int, recall: float, fpr: float, ref: References) -> str:
    if attacks < ref.n_min:
        return "too_few_attacks"
    if recall <= ref.recall - ref.drop:
        return "missed_attacks"
    if fpr > ref.fp_burst:
        return "false_positive_burst"
    return "attack_share_effect"


def window_table(
    y: np.ndarray, p: np.ndarray, category: np.ndarray, window_size: int, ref: References
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(one row per window, one row per window and attack category).

    Windows are numbered from 1, as in natural_test.csv. Trailing records that do not
    fill a window are dropped, as in the monitoring runs.
    """
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=int)
    category = np.asarray(category, dtype=object)
    n = len(y) // window_size
    rows, cats = [], []
    for w in range(n):
        sl = slice(w * window_size, (w + 1) * window_size)
        yw, pw, cw = y[sl], p[sl], category[sl]
        tp = int(((yw == 1) & (pw == 1)).sum())
        fn = int(((yw == 1) & (pw == 0)).sum())
        fp = int(((yw == 0) & (pw == 1)).sum())
        tn = int(((yw == 0) & (pw == 0)).sum())
        attacks = tp + fn
        recall = tp / attacks if attacks else float("nan")
        fpr = fp / (fp + tn) if fp + tn else float("nan")
        f1c = float(st.calibrated_f1(recall, fpr, ref.pi0)) if attacks else float("nan")
        f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
        flagged = bool(np.isfinite(f1c) and f1c <= ref.f1_calibrated - ref.drop)
        top_cat, top_missed = None, 0
        attack_mask = yw == 1
        for c in sorted(set(cw[attack_mask])):
            m = attack_mask & (cw == c)
            missed = int((m & (pw == 0)).sum())
            cats.append(
                {
                    "window": w + 1,
                    "category": c,
                    "attacks": int(m.sum()),
                    "missed": missed,
                    "recall": 1 - missed / int(m.sum()),
                }
            )
            if missed > top_missed:
                top_cat, top_missed = c, missed
        rows.append(
            {
                "window": w + 1,
                "attacks": attacks,
                "attack_share": attacks / len(yw),
                "recall": recall,
                "fpr": fpr,
                "false_positives": fp,
                "f1": f1,
                "f1_calibrated": f1c,
                "drop_from_reference": ref.f1_calibrated - f1c,
                "flagged": flagged,
                "cause": cause(attacks, recall, fpr, ref) if flagged else "",
                "top_missed_category": top_cat,
                "missed_in_top_category": top_missed,
                "top_missed_share_of_misses": top_missed / fn if fn else float("nan"),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(cats)


def category_shift(cats: pd.DataFrame, windows: list[int], baseline: list[int]) -> pd.DataFrame:
    """Attack-category mix and recall in ``windows`` against ``baseline`` windows.

    One row per category: share of attacks and recall in each group, and the
    difference. Shows whether a dip comes from more of a hard category (mix) or from
    lower recall within a category.
    """

    def group(ws: list[int]) -> pd.DataFrame:
        g = cats[cats["window"].isin(ws)].groupby("category")[["attacks", "missed"]].sum()
        g["share"] = g["attacks"] / g["attacks"].sum() if g["attacks"].sum() else np.nan
        g["recall"] = 1 - g["missed"] / g["attacks"]
        return g

    a, b = group(windows), group(baseline)
    out = a.join(b, how="outer", lsuffix="_dip", rsuffix="_baseline").fillna(
        {
            "attacks_dip": 0,
            "missed_dip": 0,
            "share_dip": 0.0,
            "attacks_baseline": 0,
            "missed_baseline": 0,
            "share_baseline": 0.0,
        }
    )
    out["share_change"] = out["share_dip"] - out["share_baseline"]
    out["recall_change"] = out["recall_dip"] - out["recall_baseline"]
    # Missed records in the dip explained by mix vs within-category recall
    total_dip = out["attacks_dip"].sum()
    miss_rate_base = (1 - out["recall_baseline"]).fillna(0)
    out["missed_expected_at_baseline_recall"] = out["attacks_dip"] * miss_rate_base
    out = out.reset_index().rename(columns={"index": "category"})
    out.attrs["attacks_dip"] = int(total_dip)
    return out.sort_values("missed_dip", ascending=False).reset_index(drop=True)
