"""Machine-specific paths.

Paths are read, in order of priority, from:

1. The environment variable ``NADMON_DATA_DIR``.
2. ``configs/paths.toml`` (local, not committed; copy ``configs/paths.example.toml``).

Generated outputs always go inside the repository (``results/`` and ``models/``),
so every machine writes to the same relative locations.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_DIR / "configs"
LOCAL_PATHS_FILE = CONFIG_DIR / "paths.toml"
EXAMPLE_PATHS_FILE = CONFIG_DIR / "paths.example.toml"

RAW_FILE_NAMES = tuple(f"UNSW-NB15_{i}.csv" for i in range(1, 5))


class ConfigError(RuntimeError):
    """Raised when the local configuration is missing or invalid."""


@dataclass(frozen=True)
class Paths:
    data_dir: Path
    project_dir: Path = PROJECT_DIR

    @property
    def results_dir(self) -> Path:
        return self.project_dir / "results"

    @property
    def models_dir(self) -> Path:
        return self.project_dir / "models"

    @property
    def raw_files(self) -> list[Path]:
        return [self.data_dir / name for name in RAW_FILE_NAMES]

    def ensure_output_dirs(self) -> None:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def check_raw_files(self) -> None:
        missing = [p for p in self.raw_files if not p.is_file()]
        if missing:
            listed = "\n  ".join(str(p) for p in missing)
            raise ConfigError(f"Raw UNSW-NB15 files not found:\n  {listed}")


def load_paths(config_file: Path = LOCAL_PATHS_FILE) -> Paths:
    env_value = os.environ.get("NADMON_DATA_DIR")
    if env_value:
        return Paths(data_dir=Path(env_value))

    if not config_file.is_file():
        raise ConfigError(
            f"No dataset path configured. Copy {EXAMPLE_PATHS_FILE.name} to "
            f"{config_file.name} in the configs folder and set data_dir, "
            "or set the NADMON_DATA_DIR environment variable."
        )

    with open(config_file, "rb") as handle:
        settings = tomllib.load(handle)

    try:
        data_dir = settings["paths"]["data_dir"]
    except KeyError as error:
        raise ConfigError(f"{config_file} must define [paths] data_dir") from error

    return Paths(data_dir=Path(data_dir))
