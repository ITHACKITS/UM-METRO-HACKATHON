"""Sentinel-1 radar (RTC, VV) from Microsoft Planetary Computer: open water seen through cloud.

Radar backscatter over calm open water is very low, so pixels below WATER_DB count as water.
Planetary Computer needs no account; its anonymous SAS token is appended to each asset URL.
Ascending and descending passes see the ground at different angles, so each pixel's history
is compared only with passes of the same direction.

Standing water inside a paddy is normal (transplanting, puddling). A flood signal therefore
comes from the surrounding ring: when the area around the field is far wetter than its own
history, water is spreading beyond the paddies.
"""

import hashlib
import json
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape

from app.config import DATA_DIR, settings
from app.ingest.http import SourceUnavailable, _client, fetch_json

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
WATER_DB = -18.0  # VV gamma0 threshold for open water, common in rice-flood mapping
RING_DEG = 0.006
TILE_DEG = 0.02
CACHE = DATA_DIR / "scene-cache" / "s1"
TILES = CACHE / "tiles"
_GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="1")

_token: dict[str, Any] = {"value": None, "expires": 0.0}
_token_lock = threading.Lock()


def _sas() -> str:
    with _token_lock:
        if _token["value"] and time.time() < _token["expires"] - 300:
            return _token["value"]
        try:
            r = _client.get(TOKEN, timeout=20)
            d = r.json()
        except Exception as e:
            raise SourceUnavailable("sentinel-1", f"token: {type(e).__name__}: {e}") from e
        _token["value"] = d["token"]
        exp = d.get("msft:expiry", "")
        try:
            _token["expires"] = datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
        except ValueError:
            _token["expires"] = time.time() + 1800
        return _token["value"]


def search(geom: dict, days: int = 120) -> tuple[list[dict], str]:
    start = (date.today() - timedelta(days=days)).isoformat()
    body = {
        "collections": ["sentinel-1-rtc"],
        "intersects": geom,
        "datetime": f"{start}/{date.today().isoformat()}",
        "limit": 60,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }
    payload, captured = fetch_json("sentinel-1", STAC, body=body, method="POST", ttl=3600, timeout=40)
    return payload.get("features", []), captured


def _vv_tile(item: dict, need: tuple) -> tuple[np.ndarray, Any, Any]:
    bounds = tuple(f(v / TILE_DEG) * TILE_DEG for f, v in zip((math.floor, math.floor, math.ceil, math.ceil), need))
    tile = TILES / f"{item['id']}_{'_'.join(f'{v:.2f}' for v in bounds)}.npz"
    if tile.exists():
        z = np.load(tile)
        meta = json.loads(str(z["meta"]))
        return z["vv"], rasterio.crs.CRS.from_wkt(meta["crs"]), rasterio.Affine(*meta["transform"])
    if settings.offline:
        raise SourceUnavailable("sentinel-1", "offline mode and scene not cached")
    href = f"{item['assets']['vv']['href']}?{_sas()}"
    with rasterio.Env(**_GDAL_ENV), rasterio.open(href) as ds:
        b = transform_bounds("EPSG:4326", ds.crs, *bounds)
        win = from_bounds(*b, ds.transform).round_offsets().round_lengths()
        vv = ds.read(1, window=win, boundless=True, fill_value=0).astype(np.float32)
        crs, tr = ds.crs, ds.window_transform(win)
    TILES.mkdir(parents=True, exist_ok=True)
    tmp = tile.with_name(f"{tile.stem}.{threading.get_ident()}.tmp.npz")
    np.savez_compressed(tmp, vv=vv, meta=np.array(json.dumps({"crs": crs.to_wkt(), "transform": list(tr)[:6]})))
    os.replace(tmp, tile)
    return vv, crs, tr


def scene_stats(item: dict, geom: dict) -> dict[str, Any]:
    CACHE.mkdir(parents=True, exist_ok=True)
    gkey = hashlib.sha1(json.dumps(geom, sort_keys=True).encode()).hexdigest()[:12]
    cf = CACHE / f"{item['id']}-{gkey}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    field = shape(geom)
    ring = field.buffer(RING_DEG)
    vv, crs, tr = _vv_tile(item, ring.bounds)
    valid = vv > 0
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10 * np.log10(vv)
    in_field = ~geometry_mask([transform_geom("EPSG:4326", crs, mapping(field))], out_shape=vv.shape, transform=tr, all_touched=True)
    in_ring = ~geometry_mask([transform_geom("EPSG:4326", crs, mapping(ring.difference(field)))], out_shape=vv.shape, transform=tr)

    def summarise(m):
        ok = m & valid
        n = int(ok.sum())
        if n < 5:
            return {"usable": False}
        return {"usable": True, "vv_db_mean": round(float(db[ok].mean()), 2), "water_fraction": round(float((db[ok] < WATER_DB).mean()), 3), "pixels": n}

    out = {
        "scene_id": item["id"],
        "datetime": item["properties"]["datetime"],
        "orbit": item["properties"].get("sat:orbit_state", "unknown"),
        "field": summarise(in_field),
        "neighbours": summarise(in_ring),
    }
    cf.write_text(json.dumps(out))
    return out


def field_timeseries(geom: dict, days: int = 120, max_scenes: int = 24) -> dict[str, Any]:
    items, captured = search(geom, days)
    items = items[:max_scenes]
    if not items:
        raise SourceUnavailable("sentinel-1", f"no Sentinel-1 scenes in the last {days} days")
    errors: list[str] = []

    def work(it):
        try:
            return scene_stats(it, geom)
        except Exception as e:
            errors.append(f"{it['id']}: {type(e).__name__}")
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        series = sorted((r for r in pool.map(work, items) if r), key=lambda r: r["datetime"])
    usable = [r for r in series if r["field"]["usable"]]
    if not usable:
        raise SourceUnavailable("sentinel-1", "no readable radar scene over the field")
    latest = usable[-1]
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(latest["datetime"].replace("Z", "+00:00"))).days
    same = [r for r in usable[:-1] if r["orbit"] == latest["orbit"] and r["neighbours"]["usable"]]
    ring_hist = [r["neighbours"]["water_fraction"] for r in same]
    ring_now = latest["neighbours"]["water_fraction"] if latest["neighbours"]["usable"] else None
    return {
        "series": series,
        "latest": latest,
        "latest_age_days": age,
        "ring_water_now": ring_now,
        "ring_water_median": round(float(np.median(ring_hist)), 3) if ring_hist else None,
        "ring_history_scenes": len(ring_hist),
        "errors": errors,
        "captured_at": captured,
        "source": "Copernicus Sentinel-1 RTC (VV) via Microsoft Planetary Computer",
    }


def flood_signal(s1: dict) -> dict | None:
    """A weighted anomaly when the surroundings are much wetter than usual on a recent pass."""
    now, med = s1.get("ring_water_now"), s1.get("ring_water_median")
    if now is None or med is None or s1["ring_history_scenes"] < 4 or s1["latest_age_days"] > 7:
        return None
    jump = now - med
    if jump < 0.15:
        return None
    weight = round(min(0.5, jump), 2)
    return {
        "kind": "flood",
        "weight": weight,
        "text": {
            "id": f"radar Sentinel-1 ({s1['latest_age_days']} hari lalu): {now:.0%} area sekitar tertutup air, biasanya {med:.0%}",
            "en": f"Sentinel-1 radar ({s1['latest_age_days']} days ago): {now:.0%} of the surroundings under water, usually {med:.0%}",
        },
    }
