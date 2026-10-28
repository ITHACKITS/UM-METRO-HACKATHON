"""Field analysis: gathers every source, runs the engine, fuses signals, explains drivers."""

import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from pyproj import Geod
from shapely.geometry import shape

from app.ai import vegetation
from app.config import settings
from app.engine import pest, recommend
from app.engine.waterbalance import FieldParams, ensemble_run, initial_state, stage_for
from app.ingest import sentinel2, terrain, weather
from app.ingest.http import SourceUnavailable

_geod = Geod(ellps="WGS84")


class FieldError(ValueError):
    pass


def field_area_ha(geom: dict) -> float:
    area, _ = _geod.geometry_area_perimeter(shape(geom))
    return abs(area) / 10_000


def validate_field(geom: dict) -> dict[str, Any]:
    try:
        poly = shape(geom)
    except Exception as e:
        raise FieldError(f"invalid geometry: {e}") from e
    if poly.geom_type != "Polygon" or not poly.is_valid:
        raise FieldError("draw one simple polygon (no self-intersections)")
    ha = field_area_ha(geom)
    if ha > settings.max_field_ha:
        raise FieldError(f"field is {ha:.0f} ha; the limit is {settings.max_field_ha:.0f} ha")
    if ha < 0.05:
        raise FieldError("field is smaller than 0.05 ha, below Sentinel-2 resolution")
    c = poly.centroid
    return {"area_ha": round(ha, 2), "lat": c.y, "lon": c.x}


def _safe(fn, *args):
    try:
        return {"ok": True, "value": fn(*args)}
    except SourceUnavailable as e:
        return {"ok": False, "source": e.source, "reason": e.reason}
    except Exception as e:
        return {"ok": False, "source": getattr(fn, "__module__", "?"), "reason": f"{type(e).__name__}: {e}"}


def gather(geom: dict, lat: float, lon: float) -> dict[str, Any]:
    jobs = {
        "weather": (weather.daily_observed_and_forecast, lat, lon),
        "ensemble": (weather.precipitation_ensemble, lat, lon),
        "climatology": (weather.climatology, lat, lon),
        "satellite": (sentinel2.field_timeseries, geom),
        "terrain": (terrain.terrain_profile, geom),
        "water": (terrain.water_features, lat, lon),
        "river": (terrain.river_discharge, lat, lon),
        "openweather": (weather.openweather_current, lat, lon),
    }
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futs = {k: pool.submit(_safe, *v) for k, v in jobs.items()}
        return {k: f.result() for k, f in futs.items()}


def _today_idx(times: list[str]) -> int:
    today = date.today().isoformat()
    return times.index(today) if today in times else 0


def _soil_now(wx: dict) -> float | None:
    h = wx["data"].get("hourly", {})
    times, sm = h.get("time", []), h.get("soil_moisture_9_to_27cm", [])
    now = datetime.now().strftime("%Y-%m-%dT%H:00")
    vals = [v for t, v in zip(times, sm) if t <= now and v is not None]
    return vals[-1] if vals else None


def _hand(field_elev: float, water: list[dict]) -> dict[str, Any] | None:
    rivers = [w for w in water if w["kind"] in {"river", "canal", "stream"} and w["distance_m"] <= 3000][:4]
    if not rivers:
        return None
    pts = [(w["nearest_point"][1], w["nearest_point"][0]) for w in rivers]
    try:
        elev, _ = terrain.elevations(pts)
    except SourceUnavailable:
        return None
    pairs = sorted(zip(elev, rivers), key=lambda p: p[0])
    e, w = pairs[0]
    return {
        "height_above_channel_m": round(field_elev - e, 1),
        "channel": w.get("name") or w["kind"],
        "channel_distance_m": w["distance_m"],
        "method": "field DEM elevation minus DEM elevation at the nearest point of the lowest nearby river/canal (HAND approximation)",
    }


def analyze(geom: dict, opts: dict | None = None) -> dict[str, Any]:
    opts = opts or {}
    meta = validate_field(geom)
    lat, lon = meta["lat"], meta["lon"]
    src = gather(geom, lat, lon)
    unavailable = [{"name": k, "source": v["source"], "reason": v["reason"]} for k, v in src.items() if not v["ok"]]
    sources: list[dict] = []

    if not src["weather"]["ok"]:
        return {"field": meta, "status": "insufficient-data", "unavailable": unavailable}

    wx = src["weather"]["value"]
    sources.append({"name": wx["source"], "captured_at": wx["captured_at"]})
    d = wx["data"]["daily"]
    ti = _today_idx(d["time"])

    # Satellite: growth stage and anomalies.
    sat = src["satellite"]["value"] if src["satellite"]["ok"] else None
    tp = {"date": None, "days_after": None, "confidence": "none", "reason": "satellite unavailable"}
    anom: dict[str, Any] = {"signals": [], "latest": None}
    if sat:
        sources.append({"name": sat["source"], "captured_at": sat["captured_at"]})
        tp = vegetation.estimate_transplanting(sat["series"])
    dat = opts.get("days_after_transplant")
    dat_basis = {"id": "diisi oleh pengguna", "en": "entered by user"}
    if dat is None:
        dat = tp["days_after"]
        conf_id = {"medium": "sedang", "low": "rendah", "none": "tidak ada"}.get(tp["confidence"], tp["confidence"])
        dat_basis = {
            "id": f"perkiraan dari Sentinel-2 (keyakinan {conf_id}): {vegetation.REASON_ID.get(tp['reason'], tp['reason'])}",
            "en": f"estimated from Sentinel-2 ({tp['confidence']} confidence): {tp['reason']}",
        }
    stage_reliable = opts.get("days_after_transplant") is not None or tp["confidence"] == "medium"
    if sat:
        anom = vegetation.anomalies(sat["series"], dat, stage_reliable)
    stage = stage_for(dat)

    params = FieldParams(days_after_transplant=dat)
    for k in ("irrigation_mm_day", "percolation_mm", "outlet_mm", "bund_mm", "drainage_mm_day", "theta_fc", "theta_wp"):
        if opts.get(k) is not None:
            setattr(params, k, float(opts[k]))

    ter = src["terrain"]["value"] if src["terrain"]["ok"] else None
    if ter:
        sources.append({"name": ter["source"], "captured_at": ter["captured_at"]})
        # Fields lower than their surroundings receive runoff from upslope.
        params.runon_factor = round(2.0 * (1 - ter["share_of_surroundings_lower"]), 2)

    latest_clear = sat["latest_clear"] if sat else None
    sat_age = sat["latest_clear_age_days"] if sat else None
    soil_theta = _soil_now(wx)
    init = initial_state(params, soil_theta, latest_clear["field"].get("water_fraction") if latest_clear else None, sat_age)
    if opts.get("initial_ponding_mm") is not None:
        init.ponding_mm = float(opts["initial_ponding_mm"])
        init.basis.append(
            {"id": f"genangan awal {init.ponding_mm:.0f} mm diisi pengguna", "en": f"ponding set to {init.ponding_mm:.0f} mm by the user"}
        )

    # Forecast drivers: ensemble rain for 15 days, deterministic ET0, then climatology to 30 days.
    horizon = int(opts.get("horizon_days", 30))
    et0_fc = d["et0_fao_evapotranspiration"][ti:]
    tmean_fc = d["temperature_2m_mean"][ti:]
    clim = src["climatology"]["value"] if src["climatology"]["ok"] else None
    if src["ensemble"]["ok"]:
        ens = src["ensemble"]["value"]
        sources.append({"name": ens["source"], "captured_at": ens["captured_at"]})
        start = ens["dates"].index(date.today().isoformat()) if date.today().isoformat() in ens["dates"] else 0
        members = [m[start:] for m in ens["members"]]
        rain_basis = {"id": f"{len(members)} anggota ensemble ECMWF", "en": f"{len(members)} ECMWF ensemble members"}
    else:
        members = [[x or 0.0 for x in d["precipitation_sum"][ti : ti + 16]]]
        rain_basis = {
            "id": "hanya ramalan tunggal (ensemble tidak tersedia): rentang ketidakpastian tidak ada",
            "en": "deterministic forecast only (ensemble unavailable): uncertainty band not available",
        }
    fc_len = len(members[0])
    dates = [(date.today() + timedelta(days=i)).isoformat() for i in range(horizon)]
    et0 = [(e if e is not None else 4.0) for e in et0_fc[:fc_len]]
    if clim and horizon > fc_len:
        sources.append({"name": clim["source"] + f", {clim['period']}", "captured_at": clim["captured_at"]})
        for i in range(fc_len, horizon):
            doy = (date.today() + timedelta(days=i)).timetuple().tm_yday
            et0.append(clim["et0"][doy])
        ext = [clim["rain"][(date.today() + timedelta(days=i)).timetuple().tm_yday] for i in range(fc_len, horizon)]
        members = [m + ext for m in members]
    else:
        horizon = fc_len
        dates = dates[:fc_len]

    # Scenario (Test mode) adjustments.
    scen = opts.get("scenario") or {}
    hypothetical = bool(scen)
    if scen:
        f = float(scen.get("rain_factor", 1.0))
        delay = int(scen.get("delay_rain_days", 0))
        dt = float(scen.get("temp_delta_c", 0.0))
        extra = scen.get("extra_rain") or []
        new_members = []
        for m in members:
            m = [x * f for x in m]
            m = [0.0 if i < delay else x for i, x in enumerate(m)]
            for ev in extra:
                i = int(ev.get("day", 0))
                if 0 <= i < len(m):
                    m[i] += float(ev.get("mm", 0))
            new_members.append(m)
        members = new_members
        if dt:
            # Hargreaves temperature term (T + 17.8) scales ET0 with warming.
            et0 = [
                e * ((t if t is not None else 27) + dt + 17.8) / ((t if t is not None else 27) + 17.8)
                for e, t in zip(et0, (tmean_fc + [27] * horizon)[:horizon])
            ]

    wb = ensemble_run(members, et0, params, init, dates)
    wb["initial_state"] = {"ponding_mm": init.ponding_mm, "depletion_mm": init.depletion_mm, "basis": init.basis}
    wb["rain_basis"] = rain_basis
    wb["forecast_days_from_ensemble"] = fc_len
    wb["et0"] = [round(e, 2) for e in et0]

    # River exposure.
    water = src["water"]["value"]["features"] if src["water"]["ok"] else []
    if src["water"]["ok"]:
        sources.append({"name": src["water"]["value"]["source"], "captured_at": src["water"]["value"]["captured_at"]})
    hand = _hand(ter["field_elevation_m"], water) if ter and water else None
    river = None
    if src["river"]["ok"]:
        rv = src["river"]["value"]
        sources.append({"name": rv["source"], "captured_at": rv["captured_at"]})
        thr = rv["return_2y_m3s"]
        mem = np.array(rv["ensemble_members"]) if rv["ensemble_members"] else None
        exceed_daily = (mem > thr).mean(axis=0).round(3).tolist() if mem is not None else []
        exceed = float((mem > thr).any(axis=1).mean()) if mem is not None else 0.0
        river = {
            "threshold_2y_m3s": thr,
            "return_5y_m3s": rv["return_5y_m3s"],
            "median_m3s": rv["p50_m3s"],
            "forecast_dates": rv["ensemble_dates"],
            "forecast_p50": np.percentile(mem, 50, axis=0).round(2).tolist() if mem is not None else [],
            "forecast_p95": np.percentile(mem, 95, axis=0).round(2).tolist() if mem is not None else [],
            "exceed_prob_daily": exceed_daily,
            "exceed_prob": round(exceed, 3),
            "history_years": rv["history_years"],
            "note": rv["note"],
        }

    # Drought fusion.
    win = min(14, len(wb["prob_stress"]))
    p_phys_d = max(wb["prob_stress"][:win]) if win else 0.0
    sig_d = [s for s in anom["signals"] if s["kind"] in {"drought", "stress"}]
    p_sat_d = 1 - math.prod(1 - s["weight"] for s in sig_d)
    p_drought = 1 - (1 - p_phys_d) * (1 - p_sat_d)

    # Flood fusion.
    p_phys_f = max(wb["prob_submerged"][:win]) if win else 0.0
    p_river = 0.0
    if river and hand:
        h = hand["height_above_channel_m"]
        exposure = 1.0 if h < 1 else 0.6 if h < 3 else 0.2 if h < 6 else 0.0
        p_river = river["exceed_prob"] * exposure
    sig_f = [s for s in anom["signals"] if s["kind"] == "flood"]
    p_sat_f = 1 - math.prod(1 - s["weight"] for s in sig_f)
    p_flood = 1 - (1 - p_phys_f) * (1 - p_river) * (1 - p_sat_f)

    def level(p):
        return "high" if p >= 0.5 else "medium" if p >= 0.2 else "low"

    conf_points = 0
    conf_points += 1 if src["ensemble"]["ok"] else 0
    conf_points += 1 if sat_age is not None and sat_age <= 15 else 0
    conf_points += 1 if dat is not None and stage_reliable else 0
    confidence = ["low", "low", "medium", "high"][conf_points]

    drought_drivers = []
    rain14 = sum(wb["rain"]["p50"][:14])
    et14 = sum(e * k for e, k in zip(wb["et0"][:14], wb["kc"][:14]))
    drought_drivers.append(
        {
            "id": f"14 hari ke depan: hujan median {rain14:.0f} mm vs kebutuhan air tanaman {et14:.0f} mm",
            "en": f"next 14 days: median rain {rain14:.0f} mm vs crop water use {et14:.0f} mm",
        }
    )
    if soil_theta is not None:
        drought_drivers.append(
            {
                "id": f"kelembapan tanah sekarang {soil_theta:.2f} m³/m³ (kapasitas lapang {params.theta_fc})",
                "en": f"soil moisture now {soil_theta:.2f} m³/m³ (field capacity {params.theta_fc})",
            }
        )
    past30 = sum(x or 0 for x in d["precipitation_sum"][max(0, ti - 30) : ti])
    if clim:
        normal30 = sum(clim["rain"][(date.today() - timedelta(days=i)).timetuple().tm_yday] for i in range(1, 31))
        drought_drivers.append(
            {
                "id": f"30 hari terakhir: hujan {past30:.0f} mm vs normal {normal30:.0f} mm (rata-rata {clim['years']} tahun)",
                "en": f"last 30 days: {past30:.0f} mm rain vs {normal30:.0f} mm normal ({clim['years']}-year mean)",
            }
        )
    drought_drivers += [s["text"] for s in sig_d]

    flood_drivers = []
    rmax = max(wb["rain"]["p95"][:14]) if win else 0
    flood_drivers.append(
        {
            "id": f"hari terbasah dalam 14 hari (skenario P95): {rmax:.0f} mm",
            "en": f"wettest day in the next 14 (P95 member): {rmax:.0f} mm",
        }
    )
    if hand:
        flood_drivers.append(
            {
                "id": f"lahan {hand['height_above_channel_m']} m di atas {hand['channel']} (berjarak {hand['channel_distance_m']} m)",
                "en": f"field is {hand['height_above_channel_m']} m above {hand['channel']} ({hand['channel_distance_m']} m away)",
            }
        )
    if river:
        flood_drivers.append(
            {
                "id": f"{river['exceed_prob']:.0%} anggota GloFAS melampaui debit banjir 2-tahunan ({river['threshold_2y_m3s']} m³/s)",
                "en": f"{river['exceed_prob']:.0%} of GloFAS members exceed the 2-year flow ({river['threshold_2y_m3s']} m³/s)",
            }
        )
    if ter:
        flood_drivers.append(
            {
                "id": f"{ter['share_of_surroundings_lower']:.0%} lahan sekitar lebih rendah dari sawah ini",
                "en": f"{ter['share_of_surroundings_lower']:.0%} of surrounding land is lower than the field",
            }
        )
    flood_drivers += [s["text"] for s in sig_f]

    drought_risk = {
        "probability": round(p_drought, 3),
        "level": level(p_drought),
        "physics_probability": round(p_phys_d, 3),
        "satellite_adjustment": round(p_sat_d, 3),
        "first_stress_day": wb["first_stress_day"],
        "drivers": drought_drivers,
    }
    flood_risk = {
        "probability": round(p_flood, 3),
        "level": level(p_flood),
        "physics_probability": round(p_phys_f, 3),
        "river_probability": round(p_river, 3),
        "satellite_adjustment": round(p_sat_f, 3),
        "max_submergence_days": wb["max_submergence_days"],
        "drivers": flood_drivers,
    }

    # Pest: last 7 observed days and next 7 forecast days.
    def day_rec(i):
        return {
            "date": d["time"][i],
            "tmean": d["temperature_2m_mean"][i],
            "tmin": d["temperature_2m_min"][i],
            "rh": d["relative_humidity_2m_mean"][i],
            "rain": d["precipitation_sum"][i],
            "wind": d["wind_speed_10m_max"][i],
        }

    pest_days = [day_rec(i) for i in range(max(0, ti - 7), min(len(d["time"]), ti + 7))]
    ndvi_now = latest_clear["field"]["ndvi_mean"] if latest_clear else None
    pests = pest.assess(pest_days, stage, ndvi_now)
    for p_ in pests:
        p_["action"] = recommend.PEST_ACTIONS.get(p_["id"])

    return {
        "status": "ok",
        "mode": "test" if hypothetical else "real",
        "hypothetical": hypothetical,
        "scenario": scen,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "field": meta,
        "crop": {
            "days_after_transplant": dat,
            "stage": stage,
            "basis": dat_basis,
            "reliable": stage_reliable,
            "transplanting_estimate": tp,
        },
        "weather": {
            "dates": d["time"],
            "today_index": ti,
            "rain": d["precipitation_sum"],
            "et0": d["et0_fao_evapotranspiration"],
            "tmax": d["temperature_2m_max"],
            "tmin": d["temperature_2m_min"],
            "rh": d["relative_humidity_2m_mean"],
            "soil_moisture_now": soil_theta,
            "openweather": src["openweather"]["value"] if src["openweather"]["ok"] else None,
        },
        "satellite": {
            "series": sat["series"] if sat else [],
            "latest_clear": latest_clear,
            "latest_clear_age_days": sat_age,
            "scenes_searched": sat["scenes_searched"] if sat else 0,
            "scenes_usable": sat["scenes_usable"] if sat else 0,
            "anomalies": {k: v for k, v in anom.items() if k != "latest"},
        },
        "terrain": ter,
        "hand": hand,
        "water_sources": water[:25],
        "river": river,
        "waterbalance": wb,
        "drought": {
            "risk": drought_risk,
            "recommendations": recommend.drought(drought_risk, stage, dat, water, wb["first_stress_day"]),
        },
        "flood": {
            "risk": flood_risk,
            "recommendations": recommend.flood(flood_risk, stage, dat, wb["max_submergence_days"], river),
        },
        "pest": pests,
        "confidence": confidence,
        "sources": sources,
        "unavailable": unavailable,
        "disclaimer": {
            "id": "Perkiraan ilmiah, bukan peringatan resmi. Untuk keputusan, ikuti BMKG, penyuluh pertanian (PPL) dan BPBD.",
            "en": "Scientific estimate, not an official warning. For decisions follow BMKG, your agricultural extension officer (PPL) and BPBD.",
        },
    }
