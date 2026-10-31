#!/usr/bin/env python3
"""Send every photo in .eval-data/samples through the running API and print the result.

Usage, with `npm run dev` running: python cv-prototype/scripts/test_samples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

SAMPLES = Path(__file__).resolve().parents[1] / ".eval-data" / "samples"
API = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000") + "/api/sigap/v1/analyze"


def summarize(body: dict) -> str:
    if body["mode"] == "disease":
        top = body["disease"]["candidates"][:1]
        return ", ".join(f"{c['class_id']} {c['score']:.2f}" for c in top) or "-"
    found = body["pest"]["detections"]
    return ", ".join(
        f"{d['class_key']} {d['score']:.2f}{'' if d['accepted'] else '?'}" for d in found[:3]
    ) or "no box"


def main() -> int:
    if not SAMPLES.is_dir():
        print(f"No samples at {SAMPLES}")
        return 1
    for folder, mode in (("disease", "disease"), ("pest", "pest"), ("other", "disease"), ("other", "pest")):
        for path in sorted((SAMPLES / folder).glob("*.jpg")):
            response = httpx.post(
                API,
                data={"mode": mode},
                files={"file": (path.name, path.read_bytes(), "image/jpeg")},
                timeout=60,
            )
            if response.status_code != 200:
                print(f"{mode:8} {path.name:46} HTTP {response.status_code}")
                continue
            body = response.json()
            print(f"{mode:8} {path.name:46} {body['status']:8} {summarize(body)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
