"""Block-level features for the P3A chair: TUAI Lancar (water turns) and TUAI Taksir (harvest estimate).

A block is a field the P3A chair has described: outline, transplanting date, variety and soil type.
Every block runs through the same analysis as the field page, with its own date and soil, so the
numbers match everywhere.
"""

import json
import os
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from shapely.geometry import Point, shape

from app.config import DATA_DIR
from app.engine import lancar, taksir
from app.ingest import soil
from app.sigap import reports

Analyze = Callable[[dict, dict], dict]
DECISIONS = DATA_DIR / "lancar" / "decisions.json"
HARVESTS = DATA_DIR / "taksir" / "harvests.json"
REPORT_RADIUS_M = 300
_lock = threading.Lock()


def _read(path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _append(path, item: dict) -> dict:
    with _lock:
        items = _read(path)
        items.append(item)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    return item


def _centroid(geom: dict) -> tuple[float, float]:
    c = shape(geom).centroid
    return c.y, c.x


def _run(block: dict, analyze: Analyze) -> tuple[dict, dict]:
    lat, lon = _centroid(block["geometry"])
    s = soil.resolve(block.get("soil"), lat, lon)
    opts: dict[str, Any] = {"soil": s["class"]}
    dat = lancar.days_after_transplant(block.get("planting_date"))
    if dat is not None:
        opts["days_after_transplant"] = max(-30, min(200, dat))
    block = {**block, "_soil": {"class": s["class"], "name": s["name"], "basis": s["basis"]}}
    return block, analyze(block["geometry"], opts)


def _each(blocks: list[dict], analyze: Analyze) -> list[tuple[dict, dict | None, str | None]]:
    def work(b):
        try:
            nb, a = _run(b, analyze)
            if a.get("status") != "ok":
                return nb, None, "weather data unavailable"
            return nb, a, None
        except Exception as e:
            return b, None, f"{type(e).__name__}: {e}"

    # Two at a time, like the officer dashboard: overlaps network waits without crowding free APIs.
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(work, blocks))


def water_turns(blocks: list[dict], analyze: Analyze) -> dict[str, Any]:
    rows, skipped = [], []
    for b, a, err in _each(blocks, analyze):
        if a is None:
            skipped.append({"id": b["id"], "name": b.get("name"), "reason": err})
        else:
            rows.append(lancar.assess(b, a))
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "order": lancar.rank(rows),
        "skipped": skipped,
        "rule": {
            "id": "Merah: hitungan air FAO-56 dan TUAI Pantau sama-sama buruk. Kuning: hanya satu yang buruk, cek ke sawah. Blok merah yang sedang berbunga diairi lebih dulu.",
            "en": "Red: both the FAO-56 water count and TUAI Pantau are bad. Yellow: only one is, check the field. Red blocks that are flowering get water first.",
        },
    }


def _verified_near(block: dict, since: str | None) -> int:
    lat, lon = _centroid(block["geometry"])
    poly = shape(block["geometry"])
    n = 0
    for r in reports.listing(days=200):
        if r["status"] != "verified" or r.get("label") in (None, "sehat"):
            continue
        if since and r["created_at"][:10] < since:
            continue
        if poly.contains(Point(r["lon"], r["lat"])) or reports.meters(lat, lon, r["lat"], r["lon"]) <= REPORT_RADIUS_M:
            n += 1
    return n


def harvest_estimate(blocks: list[dict], analyze: Analyze) -> dict[str, Any]:
    rows, skipped = [], []
    for b, a, err in _each(blocks, analyze):
        if a is None:
            skipped.append({"id": b["id"], "name": b.get("name"), "reason": err})
            continue
        f = taksir.features(b, a, _verified_near(b, b.get("planting_date")))
        rows.append({"id": b["id"], "name": b.get("name"), "area_ha": a["field"]["area_ha"], "features": f})
    taksir.classify(rows)
    fitted = taksir.fit(_read(HARVESTS))
    if fitted:
        for r in rows:
            r["estimate"] = taksir.predict(fitted, r["features"])
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "regression" if fitted else "class",
        "model": None if not fitted else {k: v for k, v in fitted.items() if k != "model"},
        "blocks": rows,
        "skipped": skipped,
        "harvest_records": len(_read(HARVESTS)),
        "needs": {"records": taksir.MIN_RECORDS, "seasons": taksir.MIN_SEASONS},
        "note": {
            "id": "Musim pertama: kelas dibanding rata-rata blok, karena data panen nyata belum cukup. Angka ton/ha muncul setelah hasil timbang dua musim terkumpul.",
            "en": "Season one: a class against the block average, as real harvest data is not yet enough. Tonnes per hectare appear once two seasons of weighed harvests are in.",
        },
    }


def record_harvest(block: dict, season: str, yield_t_ha: float, analyze: Analyze) -> dict:
    """Store a weighed harvest with the block's season indicators, the training data for TUAI Taksir."""
    b, a = _run(block, analyze)
    f = taksir.features(b, a, _verified_near(b, b.get("planting_date"))) if a.get("status") == "ok" else {}
    return _append(
        HARVESTS,
        {
            "block_id": block["id"],
            "name": block.get("name"),
            "season": season,
            "yield_t_ha": yield_t_ha,
            "planting_date": block.get("planting_date"),
            "variety": block.get("variety"),
            "features": {k: f.get(k) for k in taksir.FEATURES},
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )


def harvests() -> list[dict]:
    return _read(HARVESTS)


def record_decision(item: dict) -> dict:
    return _append(DECISIONS, {**item, "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def decisions(season: str | None = None) -> list[dict]:
    items = _read(DECISIONS)
    return [d for d in items if not season or d.get("season") == season][::-1]
