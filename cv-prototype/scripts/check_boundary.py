#!/usr/bin/env python3
"""Guard the integrated TUAI repository from local/private artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONTEXT = "CONTEXT.md"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def main() -> int:
    failures: list[str] = []
    staged = git("diff", "--cached", "--name-only", "--diff-filter=ACMRD").stdout.splitlines()
    tracked_context = git("ls-files", "--error-unmatch", LOCAL_CONTEXT, check=False)
    if tracked_context.returncode == 0:
        failures.append("root CONTEXT.md is tracked; remove it from the index")

    ignored_context = git("check-ignore", "-q", LOCAL_CONTEXT, check=False)
    if ignored_context.returncode == 0:
        failures.append("root CONTEXT.md is ignored; remove the ignore rule")

    forbidden_fragments = (
        "/private-data/",
        "/uploads/",
        "/evaluation/private/",
        "/.models/",
    )
    sensitive = [
        path
        for path in staged
        if any(fragment in f"/{path}" for fragment in forbidden_fragments)
        or path.endswith((".pt", ".pth", ".onnx", ".safetensors"))
    ]
    if sensitive:
        failures.append("model/private artifacts are staged: " + ", ".join(sensitive))

    if failures:
        print("Boundary check FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Repository guard passed ({len(staged)} staged path(s)).")
    print("CONTEXT.md is untracked and unignored; no private/model artifact is staged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

