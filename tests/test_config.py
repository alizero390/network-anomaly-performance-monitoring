from pathlib import Path

import pytest

from nadmon.config import ConfigError, load_paths


def test_environment_variable_overrides_config(monkeypatch, tmp_path):
    monkeypatch.setenv("NADMON_DATA_DIR", str(tmp_path))
    assert load_paths(tmp_path / "missing.toml").data_dir == tmp_path


def test_missing_config_gives_helpful_error(monkeypatch, tmp_path):
    monkeypatch.delenv("NADMON_DATA_DIR", raising=False)
    with pytest.raises(ConfigError, match="paths.example.toml"):
        load_paths(tmp_path / "paths.toml")


def test_reads_data_dir_from_toml(monkeypatch, tmp_path):
    monkeypatch.delenv("NADMON_DATA_DIR", raising=False)
    config = tmp_path / "paths.toml"
    config.write_text('[paths]\ndata_dir = "E:/UNSW-Dataset Original"\n', encoding="utf-8")
    paths = load_paths(config)
    assert paths.data_dir == Path("E:/UNSW-Dataset Original")
    assert [p.name for p in paths.raw_files][-1] == "UNSW-NB15_4.csv"


def test_missing_raw_files_are_reported(tmp_path):
    from nadmon.config import Paths

    with pytest.raises(ConfigError, match="UNSW-NB15_1.csv"):
        Paths(data_dir=tmp_path).check_raw_files()
