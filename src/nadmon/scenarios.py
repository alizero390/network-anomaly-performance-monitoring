"""Controlled monitoring scenarios built by resampling real records (design spec D3, D4).

Records are grouped into strata: attack strata (for example by attack category) and
benign strata (for example by service). A *composition* says what share of a window is
attacks and how attacks and benign records are spread over their strata. A stream is
a sequence of windows whose records are drawn, with replacement, from the strata in the
proportions of the composition; the composition changes at the onset window. No feature
value is edited, so every record in a stream is a real record with the frozen model's
real prediction.

Ground truth (D4) comes from each stratum's recall (attack strata) or false positive
rate (benign strata), measured on the partition the stream is drawn from:

- harmful: expected calibrated F1 falls by at least ``HARMFUL_DROP`` (0.10);
- harmless: it changes by less than ``HARMLESS_CHANGE`` (0.02) and the record mix
  changes by at least ``MIN_INPUT_CHANGE`` (total variation distance over strata);
- anything else is not used.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from nadmon.attack_share import calibrated_f1

HARMFUL_DROP = 0.10
HARMLESS_CHANGE = 0.02
MIN_INPUT_CHANGE = 0.10
MIN_STRATUM_RECORDS = 50
ALPHA_GRID = tuple(round(a, 2) for a in np.arange(0.1, 1.01, 0.1))


# ----------------------------------------------------------------------------
# Strata
# ----------------------------------------------------------------------------


def stratum_rates(strata: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    """Per stratum: class, records, positive predictions and rate.

    ``rate`` is recall for an attack stratum and FPR for a benign stratum. Every
    stratum must contain a single class.
    """
    df = pd.DataFrame({"stratum": strata, "y": y_true, "p": y_pred})
    g = df.groupby("stratum", sort=True)
    out = pd.DataFrame(
        {
            "attack": g["y"].max().astype(bool),
            "mixed": g["y"].min() != g["y"].max(),
            "records": g.size(),
            "flagged": g["p"].sum(),
        }
    )
    if out["mixed"].any():
        bad = list(out.index[out["mixed"]])
        raise ValueError(f"strata must contain one class only: {bad}")
    out["rate"] = out["flagged"] / out["records"]
    return out.drop(columns="mixed")


def unsw_strata(
    labels: np.ndarray,
    categories: np.ndarray,
    services: np.ndarray,
    protos: np.ndarray | None = None,
    states: np.ndarray | None = None,
) -> np.ndarray:
    """UNSW-NB15 strata: ``A:<attack category>`` for attacks, ``B:<service>`` for benign.

    The service value ``-`` (no identified service) becomes ``none``. With ``protos`` and
    ``states``, benign strata are finer: ``B:<service>|<proto>|<state>``.
    """
    labels = np.asarray(labels)

    def clean(values):
        return (
            pd.Series(np.asarray(values, dtype=str)).str.strip().replace({"-": "none", "": "none"})
        )

    benign = clean(services)
    if protos is not None and states is not None:
        benign = benign + "|" + clean(protos) + "|" + clean(states)
    cat = pd.Series(np.asarray(categories, dtype=str)).str.strip()
    return np.where(labels == 1, "A:" + cat, "B:" + benign).astype(str)


def stratum_index(strata: np.ndarray) -> dict[str, np.ndarray]:
    """Record positions of each stratum."""
    s = pd.Series(np.asarray(strata))
    return {k: v.to_numpy() for k, v in s.groupby(s).groups.items()}


# ----------------------------------------------------------------------------
# Compositions
# ----------------------------------------------------------------------------


def _normalise(weights: Mapping[str, float]) -> dict[str, float]:
    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("weights must have a positive sum")
    return {k: float(v) / total for k, v in weights.items() if v > 0}


@dataclass(frozen=True)
class Composition:
    attack_share: float
    attack_mix: Mapping[str, float]
    benign_mix: Mapping[str, float]

    def record_mix(self) -> dict[str, float]:
        """Share of all records in each stratum."""
        mix = {k: self.attack_share * w for k, w in self.attack_mix.items()}
        mix.update({k: (1 - self.attack_share) * w for k, w in self.benign_mix.items()})
        return mix


def base_composition(rates: pd.DataFrame) -> Composition:
    """The partition's own composition."""
    att, ben = rates[rates["attack"]], rates[~rates["attack"]]
    return Composition(
        attack_share=float(att["records"].sum() / rates["records"].sum()),
        attack_mix=_normalise(att["records"].to_dict()),
        benign_mix=_normalise(ben["records"].to_dict()),
    )


def shift_mix(mix: Mapping[str, float], targets: Iterable[str], alpha: float) -> dict[str, float]:
    """Move a fraction ``alpha`` of the mix onto ``targets``, keeping their relative sizes."""
    targets = [t for t in targets if mix.get(t, 0) > 0]
    if not targets:
        raise ValueError("no target stratum is present in the mix")
    target_mix = _normalise({t: mix[t] for t in targets})
    keys = sorted(set(mix) | set(target_mix))  # sorted: dict order must not follow hashing
    return _normalise(
        {k: (1 - alpha) * mix.get(k, 0.0) + alpha * target_mix.get(k, 0.0) for k in keys}
    )


def expected_rates(comp: Composition, rates: pd.DataFrame) -> tuple[float, float]:
    """Expected (recall, FPR) of a window with this composition."""
    r = rates["rate"]
    recall = sum(w * r[k] for k, w in comp.attack_mix.items())
    fpr = sum(w * r[k] for k, w in comp.benign_mix.items())
    return float(recall), float(fpr)


def expected_calibrated_f1(comp: Composition, rates: pd.DataFrame, pi0: float) -> float:
    recall, fpr = expected_rates(comp, rates)
    return float(calibrated_f1(recall, fpr, pi0))


def mix_distance(a: Composition, b: Composition) -> float:
    """Total variation distance between the stratum mixes of two compositions."""
    ma, mb = a.record_mix(), b.record_mix()
    return 0.5 * sum(abs(ma.get(k, 0.0) - mb.get(k, 0.0)) for k in sorted(set(ma) | set(mb)))


def ground_truth(
    before: Composition, after: Composition, rates: pd.DataFrame, pi0: float
) -> dict[str, float | str]:
    """D4 classification of a change from ``before`` to ``after``."""
    f0 = expected_calibrated_f1(before, rates, pi0)
    f1 = expected_calibrated_f1(after, rates, pi0)
    d = mix_distance(before, after)
    change = f1 - f0
    if change <= -HARMFUL_DROP:
        label = "harmful"
    elif abs(change) < HARMLESS_CHANGE and d >= MIN_INPUT_CHANGE:
        label = "harmless"
    elif d == 0 and abs(change) < HARMLESS_CHANGE:
        label = "stable"
    else:
        label = "ambiguous"
    r0, p0 = expected_rates(before, rates)
    r1, p1 = expected_rates(after, rates)
    return {
        "label": label,
        "cal_f1_before": f0,
        "cal_f1_after": f1,
        "cal_f1_change": change,
        "recall_before": r0,
        "recall_after": r1,
        "fpr_before": p0,
        "fpr_after": p1,
        "attack_share_after": after.attack_share,
        "mix_distance": d,
    }


# ----------------------------------------------------------------------------
# Standard scenarios (D3)
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    name: str
    intended: str  # "stable", "harmless" or "harmful"
    before: Composition
    after: Composition
    note: str = ""
    ramp: int = 0  # windows over which the change builds up; 0 = abrupt


def _smallest_harmful(base, make, rates, pi0) -> tuple[Composition | None, float | None]:
    for a in ALPHA_GRID:
        comp = make(a)
        if ground_truth(base, comp, rates, pi0)["label"] == "harmful":
            return comp, a
    return None, None


def _replace_largest(
    mix: Mapping[str, float], candidates: pd.DataFrame, rates: pd.DataFrame, tolerance: float
) -> tuple[dict[str, float], str, list[str]] | None:
    """Hand the largest candidate stratum's share to candidates with a similar rate.

    Strata outside ``candidates`` keep their share. Returns (new mix, donor, receivers),
    or None when no candidate has a rate within ``tolerance`` of the donor's.
    """
    present = [k for k in candidates.index if mix.get(k, 0) > 0]
    if len(present) < 2:
        return None
    donor = max(present, key=lambda k: mix[k])
    receivers = [
        k
        for k in present
        if k != donor and abs(rates.loc[k, "rate"] - rates.loc[donor, "rate"]) <= tolerance
    ]
    if not receivers:
        return None
    new = dict(mix)
    moved = new.pop(donor)
    total = sum(new[k] for k in receivers)
    for k in receivers:
        new[k] += moved * new[k] / total
    return _normalise(new), donor, receivers


def standard_scenarios(
    rates: pd.DataFrame,
    pi0: float,
    low_share: float = 0.02,
    fpr_tolerance: float = 0.005,
    recall_tolerance: float = 0.03,
    hard_gap: float = 0.20,
) -> list[Scenario]:
    """S0, H1-H3 and X1-X2 from the stratum rates of one partition.

    H1 lowers the attack share. H2 replaces the largest benign service by other services
    with nearly the same FPR (noisy services keep their share). H3 replaces the largest
    attack type by attack types with nearly the same recall (hard types keep their share).
    Harmful shifts use the smallest alpha in ``ALPHA_GRID`` that reaches the harmful
    threshold. A scenario that cannot be built is left out and
    reported by :func:`scenario_table` callers through its absence.
    """
    base = base_composition(rates)
    big = rates[rates["records"] >= MIN_STRATUM_RECORDS]
    att, ben = big[big["attack"]], big[~big["attack"]]
    recall0, fpr0 = expected_rates(base, rates)

    out = [Scenario("S0_stable", "stable", base, base)]
    out.append(
        Scenario(
            "H1_fewer_attacks",
            "harmless",
            base,
            replace(base, attack_share=low_share),
            f"attack share {base.attack_share:.3f} -> {low_share}",
        )
    )
    noisy = max(2 * fpr0, fpr0 + fpr_tolerance)
    h2 = _replace_largest(base.benign_mix, ben[ben["rate"] < noisy], rates, fpr_tolerance)
    if h2 is not None:
        mix, donor, receivers = h2
        out.append(
            Scenario(
                "H2_benign_mix",
                "harmless",
                base,
                replace(base, benign_mix=mix),
                f"{donor} replaced by: " + ", ".join(map(str, receivers)),
            )
        )
    h3 = _replace_largest(
        base.attack_mix, att[att["rate"] > recall0 - hard_gap], rates, recall_tolerance
    )
    if h3 is not None:
        mix, donor, receivers = h3
        out.append(
            Scenario(
                "H3_easy_attack_mix",
                "harmless",
                base,
                replace(base, attack_mix=mix),
                f"{donor} replaced by: " + ", ".join(map(str, receivers)),
            )
        )
    hard_attack = att.index[att["rate"] <= recall0 - hard_gap]
    if len(hard_attack):
        comp, a = _smallest_harmful(
            base,
            lambda a: replace(base, attack_mix=shift_mix(base.attack_mix, hard_attack, a)),
            rates,
            pi0,
        )
        if comp is not None:
            out.append(
                Scenario(
                    "X1_hard_attack_mix",
                    "harmful",
                    base,
                    comp,
                    f"alpha {a} towards: " + ", ".join(map(str, hard_attack)),
                )
            )
    noisy_benign = ben.index[ben["rate"] >= max(2 * fpr0, fpr0 + fpr_tolerance)]
    if len(noisy_benign):
        comp, a = _smallest_harmful(
            base,
            lambda a: replace(base, benign_mix=shift_mix(base.benign_mix, noisy_benign, a)),
            rates,
            pi0,
        )
        if comp is not None:
            out.append(
                Scenario(
                    "X2_false_positive_burst",
                    "harmful",
                    base,
                    comp,
                    f"alpha {a} towards: " + ", ".join(map(str, noisy_benign)),
                )
            )
    return out


def scenario_table(scenarios: list[Scenario], rates: pd.DataFrame, pi0: float) -> pd.DataFrame:
    """One row per scenario: intended label, computed ground truth and its numbers."""
    rows = []
    for s in scenarios:
        gt = ground_truth(s.before, s.after, rates, pi0)
        rows.append({"scenario": s.name, "intended": s.intended, **gt, "note": s.note})
    table = pd.DataFrame(rows)
    table["usable"] = table["intended"] == table["label"]
    return table


# ----------------------------------------------------------------------------
# Streams
# ----------------------------------------------------------------------------


def _blend(a: Composition, b: Composition, t: float) -> Composition:
    # Sorted keys: the order of the mix decides which stratum gets which multinomial draw
    # in build_stream, so it must not depend on Python's string hashing (fixed 2026-11-26).
    keys_a = sorted(set(a.attack_mix) | set(b.attack_mix))
    keys_b = sorted(set(a.benign_mix) | set(b.benign_mix))
    return Composition(
        attack_share=(1 - t) * a.attack_share + t * b.attack_share,
        attack_mix={
            k: (1 - t) * a.attack_mix.get(k, 0) + t * b.attack_mix.get(k, 0) for k in keys_a
        },
        benign_mix={
            k: (1 - t) * a.benign_mix.get(k, 0) + t * b.benign_mix.get(k, 0) for k in keys_b
        },
    )


def window_compositions(
    scenario: Scenario, n_windows: int = 40, onset: int = 20, ramp: int | None = None
) -> list[Composition]:
    """Composition of each window (0-based). ``onset`` is the first changed window.

    With ``ramp`` > 0 the change grows linearly and is complete at ``onset + ramp - 1``.
    ``ramp=None`` uses the scenario's own ``ramp``.
    """
    ramp = scenario.ramp if ramp is None else ramp
    if not 0 < onset < n_windows:
        raise ValueError("onset must be inside the stream")
    out = []
    for w in range(n_windows):
        if w < onset:
            t = 0.0
        elif ramp <= 0:
            t = 1.0
        else:
            t = min(1.0, (w - onset + 1) / ramp)
        out.append(_blend(scenario.before, scenario.after, t))
    return out


def build_stream(
    scenario: Scenario,
    index: Mapping[str, np.ndarray],
    rng: np.random.Generator,
    window_size: int = 5000,
    n_windows: int = 40,
    onset: int = 20,
    ramp: int | None = None,
) -> np.ndarray:
    """Record positions for one stream: ``n_windows * window_size`` indices.

    Each window's stratum counts are drawn from a multinomial with its composition, so
    windows vary as real windows do; records are then drawn with replacement within
    each stratum and shuffled within the window.
    """
    parts = []
    for comp in window_compositions(scenario, n_windows, onset, ramp):
        n_att = int(round(comp.attack_share * window_size))
        chosen = []
        for mix, n in ((comp.attack_mix, n_att), (comp.benign_mix, window_size - n_att)):
            keys = [k for k, w in mix.items() if w > 0]
            if not keys or n == 0:
                continue
            weights = np.array([mix[k] for k in keys])
            counts = rng.multinomial(n, weights / weights.sum())
            for k, c in zip(keys, counts, strict=True):
                if c:
                    pool = index[k]
                    chosen.append(pool[rng.integers(0, len(pool), size=c)])
        window = np.concatenate(chosen)
        rng.shuffle(window)
        parts.append(window)
    return np.concatenate(parts)


def harder_variants(
    scenarios: list[Scenario], low_share: float = 0.02, ramp: int = 10
) -> list[Scenario]:
    """Extra harmful scenarios (approved 2026-11-12, extending D3).

    For each harmful scenario: ``<name>_rare`` makes the same change while the attack
    share also falls to ``low_share`` (labelled attacks become scarce; the ground truth
    is unchanged because calibrated F1 does not depend on the attack share), and
    ``<name>_gradual`` builds the same change up over ``ramp`` windows.
    """
    out = []
    for s in scenarios:
        if s.intended != "harmful":
            continue
        out.append(
            replace(
                s,
                name=f"{s.name}_rare",
                after=replace(s.after, attack_share=low_share),
                note=f"{s.note}; attack share -> {low_share}",
            )
        )
        out.append(replace(s, name=f"{s.name}_gradual", ramp=ramp, note=f"{s.note}; ramp {ramp}"))
    return out
