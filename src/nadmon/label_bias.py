"""Label-bias study for Paper 2 (RESEARCH_DECISIONS.md D17, fixed before any run).

How does the way analysts choose which records to label affect performance monitoring,
and does inverse-probability weighting (B_ipw) repair it?

The grid is fixed here, before results exist:

- **Policies:** predicted attacks labelled with ``p_alert`` in {1.0, 0.9, 0.7, 0.5};
  records predicted normal with ``p_normal`` in {0.5, 0.2, 0.1, 0.05, 0.02, 0.01}. The
  two smallest values of ``p_normal`` correspond to a small random **audit sample** of
  unflagged traffic.
- **Wrong probabilities:** for (0.9, 0.1) and the audit policy (0.9, 0.02), B_ipw is
  weighted with the wrong ``p_normal`` (half and double the true value) and, once, with
  the wrong ``p_alert`` (0.7 instead of 0.9).
- **Reference conditions:** random labelling at 100% and 20%.
- Label delay 5 windows throughout.
- Strategies: B_F1, B, B_ipw (approved eligibility rule, D8) and B_ipw_eff (pooling and
  eligibility on the weighted counts).
- Scenarios: S0, H1, X1, X2 and the `_rare` variants of X1 and X2.
"""

from __future__ import annotations

from nadmon.experiment import Condition

DELAY = 5
P_ALERT_GRID = (1.0, 0.9, 0.7, 0.5)
P_NORMAL_GRID = (0.5, 0.2, 0.1, 0.05, 0.02, 0.01)
SCENARIOS = (
    "S0_stable",
    "H1_fewer_attacks",
    "X1_hard_attack_mix",
    "X2_false_positive_burst",
    "X1_hard_attack_mix_rare",
    "X2_false_positive_burst_rare",
)


def _pct(v: float) -> str:
    return f"{round(v * 100):02d}"


def policy_conditions(delay: int = DELAY) -> list[Condition]:
    """The fixed D17 grid of label conditions."""
    out = [
        Condition(f"random_p100_d{delay}", delay, 1.0),
        Condition(f"random_p20_d{delay}", delay, 0.2),
    ]
    for pa in P_ALERT_GRID:
        for pn in P_NORMAL_GRID:
            out.append(
                Condition(
                    f"pa{_pct(pa)}_pn{_pct(pn)}_d{delay}",
                    delay,
                    1.0,
                    mode="alert_first",
                    p_alert=pa,
                    p_normal=pn,
                )
            )
    for pa, pn in ((0.9, 0.1), (0.9, 0.02)):
        for factor, tag in ((0.5, "half"), (2.0, "double")):
            out.append(
                Condition(
                    f"pa{_pct(pa)}_pn{_pct(pn)}_d{delay}_assume_pn_{tag}",
                    delay,
                    1.0,
                    mode="alert_first",
                    p_alert=pa,
                    p_normal=pn,
                    assumed_p_normal=pn * factor,
                )
            )
        out.append(
            Condition(
                f"pa{_pct(pa)}_pn{_pct(pn)}_d{delay}_assume_pa70",
                delay,
                1.0,
                mode="alert_first",
                p_alert=pa,
                p_normal=pn,
                assumed_p_alert=0.7,
            )
        )
    return out


def parse_condition(name: str) -> dict:
    """Policy parts of a condition name, for tables: p_alert, p_normal, misspecification."""
    if name.startswith("random"):
        return {"policy": "random", "p_alert": None, "p_normal": None, "weights": "correct"}
    parts = name.split("_")
    pa = int(parts[0][2:]) / 100
    pn = int(parts[1][2:]) / 100
    weights = "correct"
    if "assume" in name:
        weights = "_".join(parts[parts.index("assume") + 1 :])
    return {"policy": "alert_first", "p_alert": pa, "p_normal": pn, "weights": weights}
