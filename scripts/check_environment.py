"""Check that this machine matches the pinned research environment.

Usage:  python scripts/check_environment.py

Exits with status 1 if anything needs fixing.
"""

from __future__ import annotations

import re
import sys
import warnings
from importlib import metadata

from nadmon.config import PROJECT_DIR, ConfigError, load_paths

REQUIREMENTS = PROJECT_DIR / "requirements.txt"
MODEL = PROJECT_DIR / "models" / "random_forest_baseline.joblib"


def pinned_requirements() -> dict[str, str]:
    pins = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_.\-]+)==([^\s#;]+)", line)
        if match:
            pins[match.group(1).lower()] = match.group(2)
    return pins


def main() -> int:
    problems = 0
    print(f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 11):  # noqa: UP036 - runs before install checks
        print("  ! Python 3.11 or newer is required")
        problems += 1

    print("\nPackages")
    for name, wanted in pinned_requirements().items():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        ok = installed == wanted
        problems += not ok
        mark = "ok" if ok else "MISMATCH"
        print(f"  {name:<14} wanted {wanted:<10} installed {installed}  {mark}")

    print("\nDataset")
    try:
        paths = load_paths()
        paths.check_raw_files()
        print(f"  ok  {paths.data_dir}")
    except ConfigError as error:
        print(f"  ! {error}")
        problems += 1

    print("\nBaseline model")
    if MODEL.is_file():
        import joblib

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            try:
                joblib.load(MODEL)
                print("  ok  loads without version warnings")
            except Exception as error:  # noqa: BLE001 - report any load problem
                print(f"  ! {type(error).__name__}: {str(error)[:200]}")
                problems += 1
    else:
        print("  -   not present (run scripts/baseline.py or copy it into models/)")

    print("\nAll checks passed." if not problems else f"\n{problems} problem(s) found.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
