# API contract

Base path `/api`. JSON in and out. Text meant for people comes as `{ "id": "...", "en": "..." }`.

## POST /api/analyze

```json
{
  "geometry": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] },
  "days_after_transplant": 45,          // optional, -30..200
  "irrigation_mm_day": 5,               // optional, 0..50
  "initial_ponding_mm": 30,             // optional, 0..300
  "scenario": {                         // optional; result is marked hypothetical
    "rain_factor": 0.5, "delay_rain_days": 7, "temp_delta_c": 1.5,
    "extra_rain": [{ "day": 3, "mm": 120 }]
  }
}
```

Response (abridged):

```json
{
  "status": "ok", "mode": "real|test", "hypothetical": false, "generated_at": "...",
  "field": { "area_ha": 10.46, "lat": -5.0998, "lon": 105.3356 },
  "crop": { "days_after_transplant": 49, "stage": "development", "basis": {"id": "...", "en": "..."}, "reliable": false },
  "weather": { "dates": [...], "rain": [...], "et0": [...], "soil_moisture_now": 0.277 },
  "satellite": { "series": [...], "latest_clear": {...}, "latest_clear_age_days": 10, "anomalies": {...} },
  "terrain": {...}, "hand": {...} | null, "water_sources": [...], "river": {...} | null,
  "waterbalance": { "dates": [...], "members": 51, "ponding": {"p5":[],"p50":[],"p95":[]}, "ks": {...},
                    "prob_stress": [...], "prob_submerged": [...], "first_stress_day": {...}, "params": {...} },
  "drought": { "risk": { "probability": 0.92, "level": "high", "drivers": [...] }, "recommendations": [...] },
  "flood":   { "risk": {...}, "recommendations": [...] },
  "pest": [{ "id": "blast", "level": "low", "reason": {...}, "action": {...} }],
  "confidence": "medium",
  "sources": [{ "name": "...", "captured_at": "..." }],
  "unavailable": [{ "name": "water", "source": "osm-overpass", "reason": "..." }],
  "disclaimer": {...}
}
```

If weather itself is unavailable: `{ "status": "insufficient-data", "unavailable": [...] }`. Invalid fields: HTTP 422 with the reason.

## POST /api/validate-field

`{ "geometry": ... }` → `{ "valid": true, "area_ha": 10.46, "lat": ..., "lon": ... }` or `{ "valid": false, "reason": "..." }` (always HTTP 200).

## POST /api/chat

`{ "geometry": ..., "messages": [{ "role": "user", "content": "..." }], "lang": "id", "days_after_transplant": null }` → `{ "text": "...", "engine": "llm|template", "tools_used": [...], "note": "..." }`.

## GET /api/validation?lat=&lon=

Water-balance consistency check: `{ "status": "ok", "pearson_r": 0.095, "mae_m3m3": 0.037, "is_ground_truth": false, "drought_event_skill": {"status": "not_testable", ...}, ... }`.

## POST /api/sensors/{field_id}

`{ "token": "...", "soil_moisture_m3m3": 0.31, "water_level_mm": 42, "measured_at": "..." }` → `{ "stored": true }`. Tokens live in `backend/config/sensor_tokens.json` (`{"FIELD01": "secret"}`, not committed). `GET` returns the last 200 readings.

## GET /api/health

Per-source status from the most recent calls, plus `offline_replay`, `llm` and `openweather` flags.
