"""Elevation (Copernicus DEM GLO-90 via Open-Meteo), OSM water features, GloFAS river discharge."""

import json
import math
import time
from datetime import date, timedelta
from typing import Any

import numpy as np
from shapely.geometry import LineString, Point, Polygon, shape

from app.config import DATA_DIR, settings
from app.ingest.http import SourceUnavailable, fetch_json

OSM_CACHE = DATA_DIR / "osm-cache"

OVERPASS = "https://overpass-api.de/api/interpreter"
OVERPASS_MIRROR = "https://overpass.kumi.systems/api/interpreter"


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def elevations(points: list[tuple[float, float]]) -> tuple[list[float], str]:
    out: list[float] = []
    captured = ""
    for i in range(0, len(points), 100):
        chunk = points[i : i + 100]
        payload, captured = fetch_json(
            "open-meteo-elevation",
            "https://api.open-meteo.com/v1/elevation",
            params={
                "latitude": ",".join(f"{p[0]:.5f}" for p in chunk),
                "longitude": ",".join(f"{p[1]:.5f}" for p in chunk),
            },
            ttl=86400 * 30,
        )
        out += payload.get("elevation", [])
    return out, captured


def terrain_profile(geom: dict) -> dict[str, Any]:
    poly = shape(geom)
    minx, miny, maxx, maxy = poly.bounds
    pad = 0.01  # about 1.1 km context around the field
    n = 9
    xs = np.linspace(minx - pad, maxx + pad, n)
    ys = np.linspace(miny - pad, maxy + pad, n)
    pts = [(y, x) for y in ys for x in xs]
    elev, captured = elevations(pts)
    grid = np.array(elev, dtype=float).reshape(n, n)
    c = poly.centroid
    inside = [e for (y, x), e in zip(pts, elev) if poly.contains(Point(x, y))]
    centre_elev, _ = elevations([(c.y, c.x)])
    field_elev = float(np.mean(inside)) if inside else float(centre_elev[0])
    dy = (ys[1] - ys[0]) * 111_320
    dx = (xs[1] - xs[0]) * 111_320 * math.cos(math.radians(c.y))
    gy, gx = np.gradient(grid, dy, dx)
    slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
    lower_share = float((grid < field_elev - 0.5).mean())
    return {
        "field_elevation_m": round(field_elev, 1),
        "context_min_m": round(float(grid.min()), 1),
        "context_max_m": round(float(grid.max()), 1),
        "mean_slope_deg": round(float(slope_deg.mean()), 2),
        "share_of_surroundings_lower": round(lower_share, 2),
        "grid": {"lats": ys.round(5).tolist(), "lons": xs.round(5).tolist(), "elev": grid.round(1).tolist()},
        "captured_at": captured,
        "source": "Copernicus DEM GLO-90 via Open-Meteo Elevation API",
        "note": "90 m DEM: field-scale bunds and levees are not resolved.",
    }


def water_features(lat: float, lon: float, radius_m: int = 4000) -> dict[str, Any]:
    # Mapped water features change slowly; keep a 30-day disk copy because Overpass is often overloaded.
    cache = OSM_CACHE / f"water-{lat:.3f}-{lon:.3f}-{radius_m}.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime < 30 * 86400 or settings.offline):
        return json.loads(cache.read_text(encoding="utf-8"))
    q = f"""
[out:json][timeout:25];
(
  way(around:{radius_m},{lat},{lon})["waterway"~"^(river|canal|stream|ditch|drain)$"];
  way(around:{radius_m},{lat},{lon})["natural"="water"];
  relation(around:{radius_m},{lat},{lon})["natural"="water"];
  way(around:{radius_m},{lat},{lon})["landuse"~"^(reservoir|basin)$"];
  node(around:{radius_m},{lat},{lon})["man_made"~"^(water_well|pumping_station)$"];
  node(around:{radius_m},{lat},{lon})["waterway"~"^(dam|weir|sluice_gate)$"];
);
out tags geom qt 400;
"""
    try:
        payload, captured = fetch_json("osm-overpass", OVERPASS, params={"data": q}, ttl=86400, retries=1, timeout=30)
    except SourceUnavailable:
        payload, captured = fetch_json("osm-overpass", OVERPASS_MIRROR, params={"data": q}, ttl=86400, retries=0, timeout=30)
    origin = Point(lon, lat)
    feats = []
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        kind = tags.get("waterway") or tags.get("water") or tags.get("landuse") or tags.get("man_made") or tags.get("natural")
        if el["type"] == "node":
            g = Point(el["lon"], el["lat"])
            coords = [[el["lon"], el["lat"]]]
        else:
            geo = el.get("geometry") or []
            if not geo and el["type"] == "relation":
                geo = [p for m in el.get("members", []) for p in (m.get("geometry") or [])]
            if len(geo) < 2:
                continue
            coords = [[p["lon"], p["lat"]] for p in geo]
            g = LineString(coords)
            if coords[0] == coords[-1] and len(coords) >= 4:
                g = Polygon(coords)
        nearest = g.boundary if isinstance(g, Polygon) else g
        npt = nearest.interpolate(nearest.project(origin)) if not isinstance(g, Point) else g
        dist = _haversine_m(lat, lon, npt.y, npt.x)
        feats.append(
            {
                "osm_id": f"{el['type']}/{el['id']}",
                "kind": kind,
                "name": tags.get("name"),
                "intermittent": tags.get("intermittent") == "yes" or tags.get("seasonal") == "yes",
                "distance_m": round(dist),
                "nearest_point": [round(npt.x, 6), round(npt.y, 6)],
                "geometry": coords[:200],
            }
        )
    feats.sort(key=lambda f: f["distance_m"])
    out = {
        "features": feats,
        "radius_m": radius_m,
        "captured_at": captured,
        "source": "OpenStreetMap contributors via Overpass API (ODbL)",
    }
    OSM_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


def river_discharge(lat: float, lon: float) -> dict[str, Any]:
    """GloFAS v4 forecast plus 20 years of reanalysis to place today's flow in its history."""
    fc, captured = fetch_json(
        "open-meteo-flood",
        "https://flood-api.open-meteo.com/v1/flood",
        params={
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": "river_discharge,river_discharge_median,river_discharge_max,river_discharge_min",
            "past_days": 7,
            "forecast_days": 30,
        },
        ttl=6 * 3600,
    )
    end = date.today() - timedelta(days=60)
    hist, _ = fetch_json(
        "open-meteo-flood",
        "https://flood-api.open-meteo.com/v1/flood",
        params={
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": "river_discharge",
            "start_date": date(end.year - 20, 1, 1).isoformat(),
            "end_date": end.isoformat(),
        },
        ttl=86400 * 7,
    )
    h = [x for x in hist.get("daily", {}).get("river_discharge", []) if x is not None]
    if not h:
        raise SourceUnavailable("open-meteo-flood", "no GloFAS reanalysis at this point")
    arr = np.array(h)
    # Annual maxima give the 2-year and 5-year return levels (Gumbel by method of moments).
    days = hist["daily"]["time"]
    by_year: dict[str, float] = {}
    for t, q in zip(days, hist["daily"]["river_discharge"]):
        if q is not None:
            by_year[t[:4]] = max(by_year.get(t[:4], 0.0), q)
    am = np.array(list(by_year.values()))
    beta = am.std(ddof=1) * math.sqrt(6) / math.pi
    mu = am.mean() - 0.5772 * beta

    def rp(T):
        return mu - beta * math.log(-math.log(1 - 1 / T))

    ens, _ = fetch_json(
        "open-meteo-flood",
        "https://flood-api.open-meteo.com/v1/flood",
        params={"latitude": round(lat, 4), "longitude": round(lon, 4), "daily": "river_discharge", "ensemble": "true", "forecast_days": 30},
        ttl=6 * 3600,
    )
    ed = ens.get("daily", {})
    members = [[q or 0.0 for q in v] for k, v in sorted(ed.items()) if k.startswith("river_discharge_member")]
    return {
        "forecast": fc.get("daily", {}),
        "ensemble_dates": ed.get("time", []),
        "ensemble_members": members,
        "grid_point": [fc.get("latitude"), fc.get("longitude")],
        "p50_m3s": round(float(np.percentile(arr, 50)), 2),
        "p90_m3s": round(float(np.percentile(arr, 90)), 2),
        "p99_m3s": round(float(np.percentile(arr, 99)), 2),
        "return_2y_m3s": round(float(rp(2)), 2),
        "return_5y_m3s": round(float(rp(5)), 2),
        "history_years": len(by_year),
        "captured_at": captured,
        "source": "GloFAS v4 via Open-Meteo Flood API (5 km grid)",
        "note": "GloFAS resolves rivers on a ~5 km grid; small canals and ditches are not represented.",
    }
