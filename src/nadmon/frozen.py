"""Frozen strategy settings for the one-time test run (design spec D1).

``configs/strategies.toml`` is written by the full validation run. The test run reads
it, checks that it is final (not a quick run, consistent with the validation run's
``calibration.json``, committed), and rebuilds the calibration from it without
recalibrating anything.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tomllib
from dataclasses import replace
from pathlib import Path

from nadmon import experiment as ex


def read_config(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def config_hash(path: Path) -> str:
    """SHA-256 of the file with line endings normalised (Windows and Linux agree)."""
    text = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(text).hexdigest()


def calibration_from_config(cfg: dict) -> ex.Calibration:
    ref, b, a = cfg["reference"], cfg["strategy_b"], cfg["strategy_a"]
    q_nat = a.get("q_natural")
    return ex.Calibration(
        pi0=float(ref["attack_share"]),
        recall=float(ref["recall"]),
        n_min=int(b["n_min"]),
        reference_f1_calibrated=float(ref["f1_calibrated"]),
        reference_f1=float(ref["f1"]),
        q=float(a["q"]),
        q_natural=None if q_nat is None or math.isnan(float(q_nat)) else float(q_nat),
        periods={int(k): int(v) for k, v in cfg["strategy_c"]["association_period"].items()},
    )


def settings_from_config(cfg: dict, base: ex.Settings | None = None) -> ex.Settings:
    base = base or ex.Settings()
    b, a, s = cfg["strategy_b"], cfg["strategy_a"], cfg["streams"]
    return replace(
        base,
        window_size=int(s["window_size"]),
        n_windows=int(s["n_windows"]),
        onset=int(s["onset"]),
        seed=int(s["seed"]),
        m_min=int(b["m_min"]),
        max_span=int(b["max_span"]),
        drop=float(b["drop"]),
        consecutive=int(b["consecutive"]),
        rearm=int(b["rearm"]),
        a_alpha=float(a["alpha"]),
        a_consecutive=int(a["consecutive"]),
        a_reference_size=int(a["reference_size"]),
    )


def check_against_validation(cfg: dict, calibration_json: Path) -> list[str]:
    """Problems that make the config unusable for the test run (empty list = fine)."""
    problems = []
    if cfg.get("quick_run", True):
        problems.append("the config comes from a quick run")
    if not calibration_json.is_file():
        return problems + [f"{calibration_json} not found: run the full validation first"]
    saved = json.loads(calibration_json.read_text(encoding="utf-8"))["calibration"]
    cal = calibration_from_config(cfg)

    def differs(a, b) -> bool:
        if a is None or b is None:
            return a is not b
        return not math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-9)

    for name in (
        "pi0",
        "recall",
        "n_min",
        "reference_f1_calibrated",
        "reference_f1",
        "q",
        "q_natural",
    ):
        if differs(getattr(cal, name), saved.get(name)):
            problems.append(f"{name} differs from the validation run's calibration.json")
    saved_periods = {int(k): int(v) for k, v in saved.get("periods", {}).items()}
    if saved_periods != cal.periods:
        problems.append("association periods differ from the validation run's calibration.json")
    return problems


def committed_unchanged(path: Path, repo: Path) -> bool | None:
    """True if the file is tracked and has no uncommitted changes; None if git is missing."""
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", str(path)],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return False
    except OSError:
        return None
    return status == ""
