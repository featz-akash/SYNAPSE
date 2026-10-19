from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = (
    "README.md",
    ".gitignore",
    "pyproject.toml",
    "docs/milestones/MILESTONE_0_SPECIFICATION.md",
    "docs/milestones/MILESTONE_STATUS.md",
)


def main() -> int:
    failures = 0

    print("SYNAPSE Environment Verification")
    print("=" * 36)

    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 13):
        print("FAIL: Python 3.13 or newer is required.")
        failures += 1
    else:
        print("PASS: Python version is supported.")

    print(f"\nRepository: {ROOT}")

    for relative_path in REQUIRED_FILES:
        path = ROOT / relative_path
        if path.is_file() and path.stat().st_size > 0:
            print(f"PASS: {relative_path}")
        else:
            print(f"FAIL: {relative_path} is missing or empty.")
            failures += 1

    if sys.prefix != sys.base_prefix:
        print("\nPASS: A virtual environment is active.")
    else:
        print("\nWARN: No virtual environment appears to be active.")

    git = shutil.which("git")
    if git:
        try:
            result = subprocess.run(
                [git, "-C", str(ROOT), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                print(f"PASS: Git repository detected at {result.stdout.strip()}")
            else:
                print("WARN: Git is installed, but this directory is not a Git repository.")
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"WARN: Git verification could not complete: {exc}")
    else:
        print("WARN: Git was not found on PATH.")

    print("\n" + "=" * 36)
    if failures:
        print(f"RESULT: FAIL ({failures} required check(s) failed)")
        return 1

    print("RESULT: PASS (required environment checks passed)")
    print("Note: This does not verify dependency installation or application behavior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
