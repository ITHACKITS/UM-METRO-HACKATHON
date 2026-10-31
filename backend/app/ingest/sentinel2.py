"""Sentinel-2 L2A field statistics from Element84 Earth Search (AWS open data, no key).

Only a small window around the field and a neighbour ring is read from each
Cloud-Optimized GeoTIFF. The window is snapped to a ~2 km grid and its pixels are
cached, so neighbouring fields (a farmer group's plots) reuse one read. Pixels flagged by the scene classification layer (SCL)
as cloud, shadow, cirrus, saturated or no-data are discarded.
"""

import hashlib
import json
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape

from app.config import DATA_DIR, settings
from app.ingest.http import SourceUnavailable, fetch_json

STAC = "https://earth-search.aws.element84.com/v1/search"
# SCL classes: 4 vegetation, 5 bare soil, 6 water, 7 unclassified. Everything else is masked.
VALID_SCL = {4, 5, 6, 7}
MIN_VALID_FRACTION = 0.4
NEIGHBOUR_RING_DEG = 0.006  # about 650 m around the field

_GDAL_ENV = dict(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    AWS_NO_SIGN_REQUEST="YES",
    GDAL_HTTP_MAX_RETRY="3",
    GDAL_HTTP_RETRY_DELAY="1",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
)
SCENE_CACHE = DATA_DIR / "scene-cache"
TILE_CACHE = SCENE_CACHE / "tiles"
TILE_DEG = 0.02


def search_scenes(geom: dict, days: int = 150, max_cloud: float = 85) -> tuple[list[dict], str]:
    bounds = shape(geom).bounds
    start = (date.today() - timedelta(days=days)).isoformat()
    payload, captured = fetch_json(
        "earth-search-stac",
        STAC,
        method="POST",
        body={
            "collections": ["sentinel-2-l2a"],
            "bbox": list(bounds),
            "datetime": f"{start}T00:00:00Z/..",
            "query": {"eo:cloud_cover": {"lt": max_cloud}},
            "sortby": [{"field": "properties.datetime", "direction": "desc"}],
            "limit": 60,
        },
        ttl=3 * 3600,
    )
    feats = payload.get("features", [])
    # One tile per acquisition date is enough; prefer the lowest cloud cover.
    by_day: dict[str, dict] = {}
    for f in feats:
        d = f["properties"]["datetime"][:10]
        if d not in by_day or f["properties"]["eo:cloud_cover"] < by_day[d]["properties"]["eo:cloud_cover"]:
            by_day[d] = f
    return sorted(by_day.values(), key=lambda f: f["properties"]["datetime"], reverse=True), captured


def _read(asset: dict, bounds_wgs: tuple, out_shape: tuple[int, int] | None = None, offset_applied: bool = True):
    href = asset["href"]
    band = (asset.get("raster:bands") or [{}])[0]
    # Earth Search already removes the baseline-04.00 BOA offset when this flag is set;
    # applying raster:bands.offset again would push dark pixels negative.
    scale = band.get("scale", 1e-4)
    offset = 0.0 if offset_applied else band.get("offset", 0.0)
    with rasterio.open(href) as ds:
        b = transform_bounds("EPSG:4326", ds.crs, *bounds_wgs)
        win = from_bounds(*b, ds.transform).round_offsets().round_lengths()
        kw = {"window": win, "boundless": True, "fill_value": 0}
        if out_shape:
            arr = ds.read(1, out_shape=out_shape, resampling=Resampling.nearest, **kw)
        else:
            arr = ds.read(1, **kw)
        transform = ds.window_transform(win)
        if out_shape:
            transform = transform * transform.scale(win.width / out_shape[1], win.height / out_shape[0])
        return arr, scale, offset, ds.crs, transform


def _bands(item: dict, need: tuple) -> tuple:
    """Reflectance arrays for a grid-snapped window that contains `need` (lon/lat bounds)."""
    bounds = (
        math.floor(need[0] / TILE_DEG) * TILE_DEG,
        math.floor(need[1] / TILE_DEG) * TILE_DEG,
        math.ceil(need[2] / TILE_DEG) * TILE_DEG,
        math.ceil(need[3] / TILE_DEG) * TILE_DEG,
    )
    tile = TILE_CACHE / f"{item['id']}_{'_'.join(f'{v:.2f}' for v in bounds)}.npz"
    if tile.exists():
        z = np.load(tile)
        meta = json.loads(str(z["meta"]))
        return z["R"], z["N"], z["G"], z["S"], z["scl"], rasterio.crs.CRS.from_wkt(meta["crs"]), rasterio.Affine(*meta["transform"])
    if settings.offline:
        raise SourceUnavailable("sentinel-2", "offline mode and scene not cached")

    a = item["assets"]
    applied = bool(item["properties"].get("earthsearch:boa_offset_applied", True))
    with rasterio.Env(**_GDAL_ENV):
        red, rs, ro, crs, tr = _read(a["red"], bounds, None, applied)
        shp = red.shape
        nir, ns, no, *_ = _read(a["nir"], bounds, shp, applied)
        green, gs, go, *_ = _read(a["green"], bounds, shp, applied)
        swir, ss, so, *_ = _read(a["swir16"], bounds, shp, applied)
        scl, *_ = _read(a["scl"], bounds, shp, applied)
    R = (red * rs + ro).astype(np.float32)
    N = (nir * ns + no).astype(np.float32)
    G = (green * gs + go).astype(np.float32)
    S = (swir * ss + so).astype(np.float32)
    TILE_CACHE.mkdir(parents=True, exist_ok=True)
    meta = json.dumps({"crs": crs.to_wkt(), "transform": list(tr)[:6]})
    tmp = tile.with_name(f"{tile.stem}.{threading.get_ident()}.tmp.npz")
    np.savez_compressed(tmp, R=R, N=N, G=G, S=S, scl=scl.astype(np.uint8), meta=np.array(meta))
    os.replace(tmp, tile)  # atomic, so a parallel reader never sees half a file
    return R, N, G, S, scl, crs, tr


def scene_stats(item: dict, geom: dict) -> dict[str, Any]:
    """NDVI, NDMI (crop moisture) and open-water fraction for field and neighbour ring."""
    SCENE_CACHE.mkdir(parents=True, exist_ok=True)
    gkey = hashlib.sha1(json.dumps(geom, sort_keys=True).encode()).hexdigest()[:12]
    cache_file = SCENE_CACHE / f"{item['id']}-{gkey}.json"
    if cache_file.exists():
        # Scenes cached before the NDWI -> NDMI rename use the old key for the same index.
        out = json.loads(cache_file.read_text())
        for part in ("field", "neighbours"):
            if "ndwi_mean" in out[part]:
                out[part]["ndmi_mean"] = out[part].pop("ndwi_mean")
        return out

    field = shape(geom)
    ring_poly = field.buffer(NEIGHBOUR_RING_DEG)
    R, N, G, S, scl, crs, tr = _bands(item, ring_poly.bounds)
    shp = R.shape
    valid = np.isin(scl, list(VALID_SCL)) & (R > 0) & (N > 0) & (G > 0) & (S > 0)

    field_geom = transform_geom("EPSG:4326", crs, mapping(field))
    ring_geom = transform_geom("EPSG:4326", crs, mapping(ring_poly.difference(field)))
    in_field = ~geometry_mask([field_geom], out_shape=shp, transform=tr, all_touched=True)
    in_ring = ~geometry_mask([ring_geom], out_shape=shp, transform=tr)

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (N - R) / (N + R)
        ndmi = (N - S) / (N + S)  # NDMI (B8, B11), the same index as Gao 1996 NDWI: crop moisture
        mcf = (G - N) / (G + N)  # McFeeters 1996: open water when > 0

    def summarise(mask):
        total = int(mask.sum())
        ok = mask & valid & np.isfinite(ndvi) & np.isfinite(ndmi)
        n = int(ok.sum())
        if total == 0 or n / total < MIN_VALID_FRACTION:
            return {"valid_fraction": round(n / total, 3) if total else 0.0, "usable": False}
        return {
            "valid_fraction": round(n / total, 3),
            "usable": True,
            "ndvi_mean": round(float(np.nanmean(ndvi[ok])), 4),
            "ndvi_p10": round(float(np.nanpercentile(ndvi[ok], 10)), 4),
            "ndvi_p90": round(float(np.nanpercentile(ndvi[ok], 90)), 4),
            "ndmi_mean": round(float(np.nanmean(ndmi[ok])), 4),
            "water_fraction": round(float((mcf[ok] > 0).mean()), 4),
            "pixels": n,
        }

    out = {
        "scene_id": item["id"],
        "datetime": item["properties"]["datetime"],
        "cloud_cover_tile": item["properties"].get("eo:cloud_cover"),
        "field": summarise(in_field),
        "neighbours": summarise(in_ring),
    }
    cache_file.write_text(json.dumps(out))
    return out


def field_timeseries(geom: dict, days: int = 150, max_scenes: int = 20) -> dict[str, Any]:
    scenes, captured = search_scenes(geom, days)
    scenes = scenes[:max_scenes]
    if not scenes:
        raise SourceUnavailable("sentinel-2", f"no Sentinel-2 scenes in the last {days} days")
    results: list[dict] = []
    errors: list[str] = []

    def work(item):
        try:
            return scene_stats(item, geom)
        except Exception as e:  # one bad scene must not sink the series
            errors.append(f"{item['id']}: {type(e).__name__}")
            return None

    with ThreadPoolExecutor(max_workers=10) as pool:
        for r in pool.map(work, scenes):
            if r:
                results.append(r)
    results.sort(key=lambda r: r["datetime"])
    usable = [r for r in results if r["field"]["usable"]]
    latest_clear = usable[-1] if usable else None
    age_days = None
    if latest_clear:
        dt = datetime.fromisoformat(latest_clear["datetime"].replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt).days
    return {
        "series": results,
        "scenes_searched": len(scenes),
        "scenes_usable": len(usable),
        "latest_clear": latest_clear,
        "latest_clear_age_days": age_days,
        "errors": errors,
        "captured_at": captured,
        "source": "Copernicus Sentinel-2 L2A via Element84 Earth Search (AWS Open Data)",
    }
