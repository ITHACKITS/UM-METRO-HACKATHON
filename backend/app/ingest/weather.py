"""Weather from Open-Meteo (no key), optional OpenWeather current conditions."""

from datetime import date, timedelta
from typing import Any

from app.config import settings
from app.ingest.http import SourceUnavailable, fetch_json

DAILY_VARS = [
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
    "shortwave_radiation_sum",
]
TZ = "Asia/Jakarta"


def daily_observed_and_forecast(lat: float, lon: float, past_days: int = 60) -> dict[str, Any]:
    """Past `past_days` of model-analysed weather plus a 16-day deterministic forecast."""
    payload, captured = fetch_json(
        "open-meteo-forecast",
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": ",".join(DAILY_VARS),
            "hourly": "soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",
            "past_days": past_days,
            "forecast_days": 16,
            "timezone": TZ,
        },
        ttl=3600,
    )
    return {"data": payload, "captured_at": captured, "source": "Open-Meteo Forecast API (best-match models)"}


def precipitation_ensemble(lat: float, lon: float) -> dict[str, Any]:
    """Daily precipitation from every ECMWF IFS ensemble member (15 days)."""
    payload, captured = fetch_json(
        "open-meteo-ensemble",
        "https://ensemble-api.open-meteo.com/v1/ensemble",
        params={
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": "precipitation_sum",
            "models": "ecmwf_ifs025",
            "forecast_days": 15,
            "timezone": TZ,
        },
        ttl=3600,
    )
    daily = payload.get("daily", {})
    members = [v for k, v in sorted(daily.items()) if k.startswith("precipitation_sum")]
    members = [[x if x is not None else 0.0 for x in m] for m in members if any(x is not None for x in m)]
    if not members:
        raise SourceUnavailable("open-meteo-ensemble", "no ensemble members returned")
    return {
        "dates": daily.get("time", []),
        "members": members,
        "captured_at": captured,
        "source": "Open-Meteo Ensemble API, ECMWF IFS 0.25° ensemble",
    }


def climatology(lat: float, lon: float, years: int = 10) -> dict[str, Any]:
    """Day-of-year mean rain and ET0 from the ERA5 archive, used beyond the forecast horizon."""
    end = date.today() - timedelta(days=7)
    start = date(end.year - years, end.month, end.day)
    payload, captured = fetch_json(
        "open-meteo-archive",
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": round(lat, 3),
            "longitude": round(lon, 3),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "precipitation_sum,et0_fao_evapotranspiration",
            "timezone": TZ,
        },
        ttl=86400 * 7,
    )
    d = payload.get("daily", {})
    rain: dict[int, list[float]] = {}
    et0: dict[int, list[float]] = {}
    for t, p, e in zip(d.get("time", []), d.get("precipitation_sum", []), d.get("et0_fao_evapotranspiration", [])):
        doy = date.fromisoformat(t).timetuple().tm_yday
        if p is not None:
            rain.setdefault(doy, []).append(p)
        if e is not None:
            et0.setdefault(doy, []).append(e)

    def smooth(table: dict[int, list[float]]) -> dict[int, float]:
        # 15-day window around each day of year so one wet year does not dominate.
        out = {}
        for doy in range(1, 367):
            vals: list[float] = []
            for off in range(-7, 8):
                vals += table.get((doy + off - 1) % 366 + 1, [])
            out[doy] = sum(vals) / len(vals) if vals else 0.0
        return out

    return {
        "rain": smooth(rain),
        "et0": smooth(et0),
        "years": years,
        "period": f"{start.isoformat()} to {end.isoformat()}",
        "captured_at": captured,
        "source": "Open-Meteo Historical Weather API (ERA5 reanalysis)",
    }


def openweather_current(lat: float, lon: float) -> dict[str, Any] | None:
    if not settings.openweather_key:
        return None
    payload, captured = fetch_json(
        "openweather",
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": lat, "lon": lon, "appid": settings.openweather_key, "units": "metric"},
        ttl=600,
    )
    return {"data": payload, "captured_at": captured, "source": "OpenWeather Current Weather API"}
