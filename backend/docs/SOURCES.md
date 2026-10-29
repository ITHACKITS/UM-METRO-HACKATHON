# Data sources

Access checked live on 2026-10-28 by calling each endpoint for the demo field (−5.0998, 105.3356).

| Source | Endpoint | Used for | Update | Limits / licence | Checked |
|---|---|---|---|---|---|
| Sentinel-2 L2A, Element84 Earth Search | `POST https://earth-search.aws.element84.com/v1/search`, COG assets on `sentinel-cogs` (AWS Open Data, no sign-in) | NDVI, NDWI (Gao), open-water fraction, SCL cloud mask | 5-day revisit, ~1 day latency | Copernicus open data; windowed reads ~7 s per scene | 2026-10-28, 200 OK, 902 scenes at the point |
| Sentinel-1 RTC, Microsoft Planetary Computer | `POST https://planetarycomputer.microsoft.com/api/stac/v1/search` (`sentinel-1-rtc`), anonymous SAS token from `/api/sas/v1/token/sentinel-1-rtc` | VV open water (< −18 dB) in the field and a 650 m ring | 6-12 days | Copernicus open data; Planetary Computer terms | 2026-10-29, 200 OK, 18 scenes in 120 days |
| NOAA PSL ONI / DMI | `https://psl.noaa.gov/data/correlation/oni.data`, `https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data` | hindcast check against El Niño and the Indian Ocean Dipole | monthly | public domain (US government) | 2026-10-29, 200 OK |
| OpenStreetMap API v0.6 | `https://api.openstreetmap.org/api/0.6/map` | one-off download of farmland outlines for `config/demo_group.json` | — | ODbL; small bounding boxes only | 2026-10-29, 200 OK |
| Open-Meteo Forecast | `https://api.open-meteo.com/v1/forecast` | 60 past + 16 forecast days: rain, ET0, temperature, humidity, wind, radiation; hourly soil moisture | hourly | free non-commercial, ~10k calls/day; CC BY 4.0 | 2026-10-28, 200 OK |
| Open-Meteo Ensemble | `https://ensemble-api.open-meteo.com/v1/ensemble`, `models=ecmwf_ifs025` | 51 daily rain members, 15 days | 6-hourly | as above | 2026-10-28, 200 OK, 51 members |
| Open-Meteo Historical | `https://archive-api.open-meteo.com/v1/archive` | 10-year ERA5 rain and ET0 climatology | daily, ~5-day lag | as above | 2026-10-28, 200 OK |
| Open-Meteo Flood | `https://flood-api.open-meteo.com/v1/flood` | GloFAS v4 discharge: forecast, 50-member ensemble, 20-year history | daily | as above; 5 km grid | 2026-10-28, 200 OK |
| Open-Meteo Elevation | `https://api.open-meteo.com/v1/elevation` | Copernicus DEM GLO-90 heights | static | ≤100 points per call | 2026-10-28, 200 OK |
| OpenStreetMap Overpass | `https://overpass-api.de/api/interpreter`, mirror `overpass.kumi.systems` | rivers, canals, ponds, reservoirs, wells within 4 km | continuous | ODbL; public servers often overloaded (502/timeouts seen 2026-10-28/29) | 2026-10-28: worked once, then repeatedly unavailable |
| NASA POWER | `https://power.larc.nasa.gov/api/temporal/daily/point` | checked as a backup rain source, not yet wired in | daily | free | 2026-10-28, 200 OK |
| OpenWeather (optional) | `https://api.openweathermap.org/data/2.5/weather` | current conditions when a key is set | 10 min | free key | not checked (no key) |
| Anthropic API (optional) | Messages API via the official SDK | Si Padi chatbot (`LLM_PROVIDER=anthropic`) | — | paid key | not checked (no key); template fallback verified |
| Google Gemini API (optional) | `generate_content` via the official `google-genai` SDK, manual function calling | Si Padi chatbot (`LLM_PROVIDER=gemini`) | — | free tier key from AI Studio | tool loop unit-tested with a fake client; live call pending a key |

## Not available yet

- SoilGrids soil texture per field: defaults used instead.
- BMKG warnings: not integrated; the app points users to BMKG.
