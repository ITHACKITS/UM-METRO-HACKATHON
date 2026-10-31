#!/usr/bin/env python3
"""Run source-level checks that do not require downloading model weights."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent


def run(label: str, command: list[str], cwd: Path) -> bool:
    print(f"\n[{label}] {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode:
        print(f"[{label}] failed with status {result.returncode}", file=sys.stderr)
        return False
    return True


def main() -> int:
    venv_python = REPOSITORY / ".venv" / "bin" / "python"
    python = str(venv_python if venv_python.exists() else Path(sys.executable))
    checks: list[tuple[str, list[str], Path]] = [
        ("boundary", [python, "scripts/check_boundary.py"], PROJECT),
    ]
    if (PROJECT / "tests" / "boundary").exists():
        checks.append(
            (
                "boundary-tests",
                [python, "-m", "pytest", "-q", "tests/boundary"],
                PROJECT,
            )
        )
    if (REPOSITORY / "backend" / "tests" / "sigap").exists():
        checks.append(
            (
                "sigap-backend",
                [python, "-m", "pytest", "-q", "tests/sigap"],
                REPOSITORY / "backend",
            )
        )
    if (PROJECT / "evaluation" / "tests").exists():
        checks.append(
            ("evaluation", [python, "-m", "pytest", "-q", "evaluation/tests"], PROJECT)
        )
    if (REPOSITORY / "frontend" / "node_modules").exists():
        checks.append(
            ("frontend-typecheck", ["npm", "run", "typecheck"], REPOSITORY / "frontend")
        )
        checks.append(("frontend-tests", ["npm", "run", "test"], REPOSITORY / "frontend"))
        checks.append(("frontend-build", ["npm", "run", "build"], REPOSITORY / "frontend"))
    else:
        print("[frontend] node_modules absent; install dependencies to run UI checks.")

    results = [run(label, command, cwd) for label, command, cwd in checks]
    passed = all(results)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

