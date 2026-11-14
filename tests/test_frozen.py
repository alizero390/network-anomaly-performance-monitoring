import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from nadmon import frozen

ROOT = Path(__file__).resolve().parents[1]

CONFIG_TEXT = """\
calibrated_on = "February validation"
quick_run = false

[reference]
attack_share = 0.198
recall = 0.968
f1_calibrated = 0.9728
f1 = 0.973

[strategy_b]
n_min = 68
m_min = 500
max_span = 5
drop = 0.05
consecutive = 2
rearm = 2

[strategy_a]
q = 0.038
q_natural = 1.000000001
alpha = 0.01
consecutive = 2
reference_size = 20000

[strategy_c.association_period]
"0" = 1
"5" = 5
"10" = 10

[streams]
window_size = 5000
n_windows = 40
onset = 20
seed = 20261112
"""

SAVED = {
    "pi0": 0.198,
    "recall": 0.968,
    "n_min": 68,
    "reference_f1_calibrated": 0.9728,
    "reference_f1": 0.973,
    "q": 0.038,
    "q_natural": 1.000000001,
    "periods": {"0": 1, "5": 5, "10": 10},
}


def _write(tmp_path, text=CONFIG_TEXT, saved=SAVED):
    cfg = tmp_path / "strategies.toml"
    cfg.write_text(text, encoding="utf-8")
    cal = tmp_path / "calibration.json"
    cal.write_text(json.dumps({"calibration": saved}), encoding="utf-8")
    return cfg, cal


def test_valid_config_round_trip(tmp_path):
    cfg_path, cal_path = _write(tmp_path)
    cfg = frozen.read_config(cfg_path)
    assert frozen.check_against_validation(cfg, cal_path) == []
    cal = frozen.calibration_from_config(cfg)
    assert cal.n_min == 68 and cal.periods == {0: 1, 5: 5, 10: 10}
    s = frozen.settings_from_config(cfg)
    assert s.window_size == 5000 and s.onset == 20 and s.a_reference_size == 20000


def test_quick_run_and_mismatch_are_refused(tmp_path):
    cfg_path, cal_path = _write(
        tmp_path, CONFIG_TEXT.replace("quick_run = false", "quick_run = true")
    )
    problems = frozen.check_against_validation(frozen.read_config(cfg_path), cal_path)
    assert any("quick run" in p for p in problems)
    cfg_path, cal_path = _write(tmp_path, saved={**SAVED, "q": 0.1})
    problems = frozen.check_against_validation(frozen.read_config(cfg_path), cal_path)
    assert any(p.startswith("q differs") for p in problems)
    cfg_path, cal_path = _write(tmp_path, saved={**SAVED, "periods": {"0": 2, "5": 5, "10": 10}})
    problems = frozen.check_against_validation(frozen.read_config(cfg_path), cal_path)
    assert any("association periods" in p for p in problems)


def test_hash_ignores_line_endings(tmp_path):
    a, b = tmp_path / "a.toml", tmp_path / "b.toml"
    a.write_bytes(b"x = 1\ny = 2\n")
    b.write_bytes(b"x = 1\r\ny = 2\r\n")
    assert frozen.config_hash(a) == frozen.config_hash(b)


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_committed_unchanged(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    f = repo / "c.toml"
    f.write_text("a = 1\n")
    assert frozen.committed_unchanged(f, repo) is False  # untracked
    _git(repo, "add", "c.toml")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c")
    assert frozen.committed_unchanged(f, repo) is True
    f.write_text("a = 2\n")
    assert frozen.committed_unchanged(f, repo) is False


def _load_script():
    spec = importlib.util.spec_from_file_location("rst", ROOT / "scripts" / "run_strategy_test.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rst"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_script_guards(tmp_path, monkeypatch):
    mod = _load_script()
    cfg_path, cal_path = _write(tmp_path)
    out = tmp_path / "test_out"
    monkeypatch.setattr(mod, "CONFIG", cfg_path)
    monkeypatch.setattr(mod, "VALIDATION_CALIBRATION", cal_path)
    monkeypatch.setattr(mod, "OUT", out)
    args = SimpleNamespace(check_only=False, confirm_committed=False, resume_identical=False)

    # git cannot see the temporary file as committed -> refused
    monkeypatch.setattr(frozen, "committed_unchanged", lambda p, r: False)
    with pytest.raises(SystemExit, match="uncommitted"):
        mod.guards(args)

    # git missing -> needs --confirm-committed
    monkeypatch.setattr(frozen, "committed_unchanged", lambda p, r: None)
    with pytest.raises(SystemExit, match="confirm-committed"):
        mod.guards(args)
    args.confirm_committed = True
    assert mod.guards(args)["quick_run"] is False

    # an existing test run blocks a second one
    out.mkdir()
    (out / "run.json").write_text(json.dumps({"config_sha256": frozen.config_hash(cfg_path)}))
    with pytest.raises(SystemExit, match="used once"):
        mod.guards(args)
    args.resume_identical = True
    assert mod.guards(args)
    (out / "run.json").write_text(json.dumps({"config_sha256": "other"}))
    with pytest.raises(SystemExit, match="config changed"):
        mod.guards(args)
