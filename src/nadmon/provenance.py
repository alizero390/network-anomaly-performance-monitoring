"""Record how a result was produced (code version, environment, time)."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

from nadmon.config import PROJECT_DIR

TRACKED_PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "joblib")


def _git(*args: str) -> str | None:
    """Run the git command line tool; None if it is not installed or fails."""
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


def read_head_commit(git_dir: Path) -> str | None:
    """Read the current commit directly from the .git folder.

    Used when the git command is not on PATH (for example when Git is only
    available through GitHub Desktop).
    """
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None

    if not head.startswith("ref:"):
        return head or None  # Detached HEAD holds the commit hash itself.

    ref = head.removeprefix("ref:").strip()
    try:
        return (git_dir / ref).read_text(encoding="utf-8").strip() or None
    except OSError:
        pass

    try:
        packed = (git_dir / "packed-refs").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in packed.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0]
    return None


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in TRACKED_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def run_metadata() -> dict[str, object]:
    commit = _git("rev-parse", "HEAD")
    # Uncommitted changes to code and docs; generated results are excluded.
    status = _git("status", "--porcelain", "--", ".", ":(exclude)results")
    if commit is None:
        commit = read_head_commit(PROJECT_DIR / ".git")

    return {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit,
        # None means it could not be checked (git command line not installed).
        "git_uncommitted_changes": bool(status) if status is not None else None,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": package_versions(),
    }
