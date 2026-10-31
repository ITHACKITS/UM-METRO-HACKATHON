#!/usr/bin/env python3
"""Guard the integrated TUAI repository from local/private artifacts.

The original prototype allowed staged files only below ``cv-prototype/``.  TUAI
Sigap is now an approved page and API inside the main application, so that rule
would reject the integration it is meant to protect.  This guard now enforces
the durable boundaries instead: local memory stays visible but untracked, and
private images/model binaries never enter Git.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


FORBIDDEN_PREFIXES = (
    ".models/",
    "cv-prototype/.models/",
    "cv-prototype/private-data/",
    "cv-prototype/uploads/",
    "cv-prototype/evaluation/private/",
)
FORBIDDEN_SUFFIXES = (".onnx", ".pt", ".pth", ".safetensors")


def invalid_staged_paths(paths: list[str]) -> list[str]:
    """Return staged paths that violate the local/private-data boundary."""
    return sorted(
        path
        for path in paths
        if path == "CONTEXT.md"
        or path.startswith(FORBIDDEN_PREFIXES)
        or path.lower().endswith(FORBIDDEN_SUFFIXES)
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    staged_result = _git(root, "diff", "--cached", "--name-only", "-z")
    if staged_result.returncode:
        print(staged_result.stderr.decode(errors="replace"), file=sys.stderr)
        return 2
    staged = [
        item.decode("utf-8", errors="surrogateescape")
        for item in staged_result.stdout.split(b"\0")
        if item
    ]
    escaped = invalid_staged_paths(staged)
    failures: list[str] = []
    if escaped:
        failures.append("local/private/model artifacts are staged: " + ", ".join(escaped))

    tracked = _git(root, "ls-files", "--error-unmatch", "CONTEXT.md")
    if tracked.returncode == 0:
        failures.append("CONTEXT.md is tracked; it must remain local and untracked")
    ignored = _git(root, "check-ignore", "-q", "CONTEXT.md")
    if ignored.returncode == 0:
        failures.append("CONTEXT.md is ignored; it must remain visibly untracked")
    elif ignored.returncode not in {1}:
        failures.append("unable to determine CONTEXT.md ignore state")

    if failures:
        for failure in failures:
            print(f"BOUNDARY ERROR: {failure}", file=sys.stderr)
        return 1
    print(
        f"repository guard ok: {len(staged)} staged path(s); CONTEXT.md is "
        "untracked and unignored; no private/model artifact is staged"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

