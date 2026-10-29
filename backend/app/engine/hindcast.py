"""Dry-season hindcast: does the water balance single out the known drought years?

For each year the paddy water balance runs on ERA5 rain and ET0 through a dry-season
(gadu) crop, rainfed, transplanted on 1 June and again on 1 July. The number of
water-stress days is then compared with two climate indices measured independently
of the model, both from NOAA PSL:

- ONI (El Niño when the June-October mean is >= 0.5 °C), and
- DMI, the Indian Ocean Dipole (positive when the August-October mean is >= 0.4 °C).

Both are documented drivers of dry seasons in southern Sumatra. This tests whether the
model separates drought-prone years from wet ones; it is not a field-level validation.
A rain-only baseline (dry-season rain total) is scored the same way, so it is visible
whether the water balance adds anything over simply counting rain.
"""

from datetime import date
from typing import Any

import numpy as np

from app.engine.waterbalance import FieldParams, InitialState, run
from app.ingest.http import SourceUnavailable, fetch_json

ONI_URL = "https://psl.noaa.gov/data/correlation/oni.data"
DMI_URL = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data"
SEASON_DAYS = 110
TRANSPLANT = [(6, 1), (7, 1)]


def _psl_table(url: str, source: str) -> dict[int, list[float | None]]:
    """NOAA PSL text format: a header line, then 'year v1 ... v12', missing as -99.9/-9999."""
    from app.ingest.http import _client  # plain text, so not through fetch_json

    try:
        text = _client.get(url, timeout=30).text
    except Exception as e:
        raise SourceUnavailable(source, f"{type(e).__name__}: {e}") from e
    out: dict[int, list[float | None]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 13 and parts[0].isdigit():
            out[int(parts[0])] = [None if float(v) <= -99 else float(v) for v in parts[1:]]
    if not out:
        raise SourceUnavailable(source, "unexpected file format")
    return out


def _rank(x: np.ndarray) -> np.ndarray:
    order = x.argsort()
    r = np.empty(len(x))
    r[order] = np.arange(len(x))
    for v in np.unique(x):  # average ties
        m = x == v
        r[m] = r[m].mean()
    return r


def spearman(a: list[float], b: list[float]) -> float:
    ra, rb = _rank(np.array(a, float)), _rank(np.array(b, float))
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def auc(scores: list[float], positive: list[bool]) -> float | None:
    """Chance that a random drought-driver year scores higher than a random other year."""
    pos = [s for s, p in zip(scores, positive) if p]
    neg = [s for s, p in zip(scores, positive) if not p]
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def season_stress(dates: list[str], rain: list[float], et0: list[float], year: int) -> dict[str, float]:
    idx = {d: i for i, d in enumerate(dates)}
    stress, rain_tot = [], []
    for m, d in TRANSPLANT:
        start = date(year, m, d)
        i0 = idx.get(start.isoformat())
        if i0 is None or i0 + SEASON_DAYS > len(dates):
            continue
        r, e = rain[i0 : i0 + SEASON_DAYS], et0[i0 : i0 + SEASON_DAYS]
        out = run(r, e, FieldParams(days_after_transplant=0), InitialState(ponding_mm=50.0))
        stress.append(sum(1 for k in out["ks"] if k < 0.95))
        rain_tot.append(sum(r))
    if not stress:
        return {}
    return {"stress_days": float(np.mean(stress)), "season_rain_mm": float(np.mean(rain_tot))}


def run_hindcast(lat: float, lon: float, first: int = 2005, last: int | None = None) -> dict[str, Any]:
    last = last or date.today().year - 1
    payload, captured = fetch_json(
        "open-meteo-archive",
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": round(lat, 3),
            "longitude": round(lon, 3),
            "start_date": f"{first}-01-01",
            "end_date": f"{last}-12-31",
            "daily": "precipitation_sum,et0_fao_evapotranspiration",
            "timezone": "Asia/Jakarta",
        },
        ttl=86400 * 30,
        timeout=90,
    )
    d = payload["daily"]
    rain = [x or 0.0 for x in d["precipitation_sum"]]
    et0 = [x if x is not None else 4.0 for x in d["et0_fao_evapotranspiration"]]
    oni = _psl_table(ONI_URL, "noaa-psl-oni")
    dmi = _psl_table(DMI_URL, "noaa-psl-dmi")

    rows = []
    for y in range(first, last + 1):
        s = season_stress(d["time"], rain, et0, y)
        o = [v for v in (oni.get(y) or [])[5:10] if v is not None]
        i = [v for v in (dmi.get(y) or [])[7:10] if v is not None]
        if not s or len(o) < 5 or len(i) < 3:
            continue
        oni_m, dmi_m = float(np.mean(o)), float(np.mean(i))
        rows.append(
            {
                "year": y,
                **{k: round(v, 1) for k, v in s.items()},
                "oni_jun_oct": round(oni_m, 2),
                "dmi_aug_oct": round(dmi_m, 2),
                "el_nino": oni_m >= 0.5,
                "la_nina": oni_m <= -0.5,
                "iod_positive": dmi_m >= 0.4,
            }
        )

    stress = [r["stress_days"] for r in rows]
    dryness = [-r["season_rain_mm"] for r in rows]  # less rain = drier, so it scores like stress
    driver = [r["el_nino"] or r["iod_positive"] for r in rows]

    def score(x):
        return {
            "spearman_vs_oni": round(spearman(x, [r["oni_jun_oct"] for r in rows]), 2),
            "spearman_vs_dmi": round(spearman(x, [r["dmi_aug_oct"] for r in rows]), 2),
            "auc_driver_years": None if (a := auc(x, driver)) is None else round(a, 2),
        }

    ranked = sorted(rows, key=lambda r: -r["stress_days"])
    top = max(1, round(len(rows) / 4))
    return {
        "status": "ok",
        "check": "dry-season water-stress days (ERA5-driven water balance, rainfed) vs independent ENSO/IOD indices",
        "is_ground_truth": False,
        "location": {"lat": lat, "lon": lon},
        "years": [rows[0]["year"], rows[-1]["year"]] if rows else [],
        "season": f"{SEASON_DAYS}-day crop transplanted 1 June and 1 July, mean of the two",
        "water_balance": score(stress),
        "rain_only_baseline": score(dryness),
        "driver_years": [r["year"] for r in rows if r["el_nino"] or r["iod_positive"]],
        "top_quarter_by_stress": [r["year"] for r in ranked[:top]],
        "table": ranked,
        "sources": [
            {"name": "ERA5 via Open-Meteo archive", "captured_at": captured},
            {"name": "ONI, NOAA CPC via PSL", "url": ONI_URL},
            {"name": "DMI HadISST1.1, NOAA PSL", "url": DMI_URL},
        ],
        "note": "Indices describe the regional climate, not this field. Agreement shows the model reacts to the climate "
        "signals that drive real droughts here; field-level skill still needs farmer or extension-office records.",
    }
