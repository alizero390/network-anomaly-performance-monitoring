"""Record how a result was produced (code version, environment, time)."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata

from nadmon.config import PROJECT_DIR

TRACKED_PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "joblib")


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in TRACKED_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def run_metadata() -> dict[str, object]:
    status = _git("status", "--porcelain")
    return {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_uncommitted_changes": bool(status) if status is not None else None,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": package_versions(),
    }
