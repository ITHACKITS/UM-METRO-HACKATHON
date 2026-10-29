"""Backtest of the water balance against independent soil-moisture estimates.

Ground truth for paddy water levels does not exist for an arbitrary field, so
drought and flood event skill cannot be scored directly. Drought is scored by proxy
(engine/hindcast.py: dry-season stress vs ENSO/IOD indices). What else can be tested:
does the water balance, driven only by past rain and ET0, track the root-zone
moisture from Open-Meteo's land-surface model? That is a consistency check
between two models, and it is labelled as such.
"""

from datetime import datetime

import numpy as np

from app.engine import hindcast
from app.engine.waterbalance import FieldParams, InitialState, run
from app.ingest import weather
from app.ingest.http import SourceUnavailable


def _event_skill(lat: float, lon: float) -> dict:
    try:
        h = hindcast.run_hindcast(lat, lon)
    except SourceUnavailable as e:
        return {"status": "unavailable", "reason": str(e)}
    return {
        "status": "proxy",
        "reason": "no field-level drought records; scored against independent ENSO/IOD indices instead",
        **h,
    }


def backtest(lat: float, lon: float) -> dict:
    wx = weather.daily_observed_and_forecast(lat, lon, past_days=60)
    d = wx["data"]["daily"]
    h = wx["data"]["hourly"]
    today = datetime.now().date().isoformat()
    ti = d["time"].index(today) if today in d["time"] else len(d["time"]) - 16
    # Daily mean root-zone moisture from the hourly series.
    sm_by_day: dict[str, list[float]] = {}
    for t, v in zip(h["time"], h["soil_moisture_9_to_27cm"]):
        if v is not None:
            sm_by_day.setdefault(t[:10], []).append(v)
    days = d["time"][:ti]
    sm = [float(np.mean(sm_by_day[x])) if x in sm_by_day else None for x in days]
    if not days or sm[0] is None:
        return {"status": "not_testable", "reason": "no soil-moisture history at this point"}
    p = FieldParams(days_after_transplant=None)
    init = InitialState(depletion_mm=max(0.0, 1000 * (p.theta_fc - sm[0]) * p.root_depth_m))
    rain = [x or 0.0 for x in d["precipitation_sum"][:ti]]
    et0 = [x or 4.0 for x in d["et0_fao_evapotranspiration"][:ti]]
    out = run(rain, et0, p, init)
    sim_theta = [p.theta_fc - dr / (1000 * p.root_depth_m) for dr in out["depletion"]]
    pairs = [(s, o) for s, o in zip(sim_theta, sm) if o is not None]
    s_arr, o_arr = np.array([a for a, _ in pairs]), np.array([b for _, b in pairs])
    r = float(np.corrcoef(s_arr, o_arr)[0, 1]) if len(pairs) > 5 and s_arr.std() > 0 and o_arr.std() > 0 else None
    return {
        "status": "ok",
        "check": "water balance (rain + ET0 only) vs Open-Meteo modelled soil moisture 9-27 cm",
        "is_ground_truth": False,
        "days": len(pairs),
        "pearson_r": None if r is None else round(r, 3),
        "mae_m3m3": round(float(np.abs(s_arr - o_arr).mean()), 4),
        "series": {"dates": days, "simulated": [round(x, 4) for x in sim_theta], "reference": sm},
        "drought_event_skill": _event_skill(lat, lon),
        "flood_event_skill": {
            "status": "not_testable",
            "reason": "no field-level inundation record to score against; Sentinel-1 radar is used as a live signal only",
        },
        "source": wx["source"],
        "captured_at": wx["captured_at"],
    }
