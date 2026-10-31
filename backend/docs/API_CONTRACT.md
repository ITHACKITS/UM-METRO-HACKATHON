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

`verdict` (also in the response): `{ "status": "aman|waspada|bahaya", "threat": "drought|flood|pest|null", "probability": 0.725, "headline": {...}, "why": {...}, "today": {...}, "confidence": "medium" }`. `radar`: latest Sentinel-1 pass, its age, ring water now vs median, `flood_signal`.

## POST /api/verdict

Same body as `/api/analyze`. Returns `{ status, field, verdict, drought: {probability, level, first_stress_day}, flood: {probability, level, max_submergence_days}, pest_high, stage, scene_age_days, generated_at }`. Shares the analysis cache.

## GET /api/demo-group

`{ "name": "...", "source": "OpenStreetMap farmland ways ...", "fields": [{ "id", "name", "geometry" }] }`.

## POST /api/alerts/subscribe

`{ "geometry": ..., "name": "Sawah Pak Budi", "lang": "id", "days_after_transplant": null }` → `{ "enabled": true, "code": "...", "link": "https://t.me/<bot>?start=<code>" }`, or `{ "enabled": false }` when no bot token is set. The code is single-use; unlinked codes expire after two days.

## POST /api/validate-field

`{ "geometry": ... }` → `{ "valid": true, "area_ha": 10.46, "lat": ..., "lon": ... }` or `{ "valid": false, "reason": "..." }` (always HTTP 200).

## POST /api/chat

`{ "geometry": ..., "messages": [{ "role": "user", "content": "..." }], "lang": "id", "days_after_transplant": null }` → `{ "text": "...", "engine": "llm|template", "tools_used": [...], "note": "..." }`.

## GET /api/validation?lat=&lon=

Water-balance consistency check: `{ "status": "ok", "pearson_r": 0.095, "mae_m3m3": 0.037, "is_ground_truth": false, "drought_event_skill": {"status": "proxy", "water_balance": {"spearman_vs_oni", "spearman_vs_dmi", "auc_driver_years"}, "rain_only_baseline": {...}, "table": [...]}, ... }`.

## POST /api/sensors/{field_id}

`{ "token": "...", "soil_moisture_m3m3": 0.31, "water_level_mm": 42, "measured_at": "..." }` → `{ "stored": true }`. Tokens live in `backend/config/sensor_tokens.json` (`{"FIELD01": "secret"}`, not committed). `GET` returns the last 200 readings.

## GET /api/health

Per-source status from the most recent calls, plus `offline_replay`, `llm` and `openweather` flags.

## TUAI blocks

A block is `{ "id": "...", "name": "Petak 1", "geometry": Polygon, "planting_date": "2026-09-01" | null, "variety": "ciherang|inpari32|inpari42|ir64|mekongga|lainnya" | null, "soil": "clay|clay_loam|silt_loam|loam|sandy_loam" | null }`. A blank soil is read from SoilGrids, else clay loam.

## POST /api/analyze: `siaga`

The analysis now carries `siaga`: `{ "level": "low|medium|high", "warnings": [{ "kind": "heavy_rain|flooded|submergence_forecast", "level", "date", "text" }], "bmkg": { "area": { "adm4", "desa", "kecamatan", "distance_km" }, "days": [{ "date", "rain_mm", "max_3h_mm", "weather", "category" }], "source", "captured_at" } | null, "radar_flood": { "flooded_now", "since", "days_observed", "passes", "puddling_stage", "slope_masked", "history": [...], "method" } | null }`. Scene stats use `ndmi_mean` (formerly `ndwi_mean`).

## POST /api/lancar/rank

`{ "blocks": [Block, ...] }` (1-40) → `{ "order": [{ "id", "name", "rank", "color": "merah|kuning|hijau", "flowering", "days_after_transplant", "need_mm_7d", "need_m3_7d", "prob_stress_7d", "calc_bad", "pantau_bad", "pantau_known", "check_field", "soil": { "class", "name", "basis" }, "reasons": [Txt] }], "skipped": [...], "rule": Txt }`.

## POST /api/lancar/decisions · GET /api/lancar/decisions?season=

`{ "season": "MT1 2026/27", "block_id", "block_name", "date": "YYYY-MM-DD", "decision", "outcome", "followed_recommendation", "by" }` → stored item; GET returns `{ "decisions": [...] }`, newest first.

## POST /api/taksir

`{ "blocks": [Block, ...] }` → `{ "mode": "class|regression", "model": { "n", "seasons", "rmse_t_ha", "r2_in_sample", "coef" } | null, "blocks": [{ "id", "name", "features": { "ndvi", "ndmi", "events", "event_text", "scenes", "window" }, "class": "di_bawah|sekitar|di_atas" | null, "class_reason", "estimate": { "t_ha", "low", "high" } }], "harvest_records", "needs": { "records": 8, "seasons": 2 }, "note" }`.

## POST /api/taksir/harvest · GET /api/taksir/harvest

`{ "block": Block, "season": "MT1 2026/27", "yield_t_ha": 6.0 }` → stored record with the block's season features (the training data).

## GET /api/sigap/status

`{ "disease": { "model", "state" }, "planthopper": { "state" }, "symptoms": { "state" }, "review_below": 0.7, "classes": { key: { "key", "name", "kind", "advice", "checked_by_ppl", "source" } } }`.

## POST /api/sigap/analyze

`{ "image": "data:image/jpeg;base64,...", "part": "daun|pangkal|gejala" }` → `{ "finding": { "key", "label", "confidence", "count"? } | null, "needs_review", "review_reasons": [Txt], "models": { "disease"?, "symptoms"?, "planthopper"?: { "status", "boxes": [{ "x", "y", "w", "h", "confidence" }] (0-1 of the image), "count", "note" } }, "advice" }`. HTTP 422 for unreadable or tiny images.

## POST /api/sigap/reports · GET /api/sigap/reports?days=60

`{ "lat", "lon", "label", "source": "foto|laporan_cepat", "confidence"?, "count"?, "severity"?: "ringan|sedang|berat", "needs_review", "block_id"?, "block_name"?, "reporter"?, "note"?, "image"? }` → stored report with `id`, `status: "pending"`, `kind`, `photo`. `GET /api/sigap/reports/{id}/photo` returns the JPEG.

## POST /api/sigap/reports/{id}/review

`{ "status": "verified|rejected", "label"?, "reviewer", "note", "pin"? }` → the updated report. HTTP 403 when `SIGAP_PPL_PIN` is set and the PIN is wrong.

## POST /api/sigap/warnings

`{ "blocks": [{ "id", "lat", "lon" }] }` → `{ "blocks": { id: { "warning", "counts", "triggered" } }, "rule": { "radius_m", "min_reports", "days", "labels" }, "note" }`. Only verified `wereng` and `tikus` reports count.
