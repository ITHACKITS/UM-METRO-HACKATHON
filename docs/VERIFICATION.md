# Verification

Run on 2026-10-29, Windows 11, Chrome (ANGLE D3D11), Python 3.12, Node 24.

## Automated

| Check | Command | Result |
|---|---|---|
| Backend unit tests | `cd backend && python -m pytest -q` | 15 passed |
| Lint | `ruff check app tests` | All checks passed |
| Type check + production build | `cd frontend && npm run build` | built, no type errors |
| End-to-end | `python scripts/qa.py http://localhost:5173 <dir>` | 47 checks passed, 0 console errors, 0 failed same-origin requests |
| Production serving | API on :8011 with built `frontend/dist` | `/`, `/app`, `/credits`, `/api/health`, favicon, mascot all HTTP 200 |

The end-to-end suite covers: landing loader and diorama frames; dock water modes, stage, hour; language switch; anchor navigation; stat citation links; credits; 404; no-WebGL fallback; reduced motion; app empty state; a rejected tiny field; demo analysis; all six tabs; Indonesian drivers; day slider and player; basemap switch; water tab honesty when OSM is down; crop-age edit; scenario mode and its hypothetical banner; back to real; chatbot answers with numbers and sources; pest answer; Escape closes chat; return to landing without loader replay or style leaks; 360 px mobile overflow, tabs and tap targets.

## Failure paths checked

| Situation | Behaviour |
|---|---|
| Overpass overloaded (happened for real, repeatedly) | Water sources listed as unavailable with the reason; analysis continues; report says so |
| Tiny or invalid polygon | Rejected with a message, no request error |
| No clear Sentinel-2 scene recently | Scene age shown; ponding starts at 0 mm and the basis says why |
| Low-confidence field age | Curve-anomaly signal suppressed; confidence lowered |
| No LLM key | Template answers from the same data, labelled as templates |
| No WebGL 2 | Landing shows a message; everything else works |
| Offline | `JAGAPADI_OFFLINE=1` serves recorded real responses or reports the source as unavailable |

## Numbers traced to source (demo field, 2026-10-28/29)

| Shown | Source / calculation |
|---|---|
| Area 10.46 ha | geodesic area of the OSM-derived polygon (pyproj) |
| NDVI 0.32, NDWI −0.02 on 2026-10-18 | Sentinel-2 L2A scene S2C_48MWV_20261018, SCL-masked field pixels |
| Soil moisture 0.277 m³/m³ | Open-Meteo `soil_moisture_9_to_27cm`, current hour |
| Last 30 days rain vs normal | Open-Meteo past days vs ERA5 2016-2026 day-of-year mean |
| 51 members | ECMWF IFS 0.25° ensemble via Open-Meteo |
| 2-year flow 8.38 m³/s | Gumbel fit to 21 years of GloFAS annual maxima at the field's grid point |
| Field 43 m elevation, 6% surroundings lower | Copernicus DEM GLO-90 9×9 grid via Open-Meteo |
| Drought % and first-stress day | FAO-56 balance per ensemble member (see README method) |
| Pest levels | favourable-day counts over the last and next 7 days of Open-Meteo weather |
| Rice-loss statistics on the landing | BPS and Kementan figures, linked to the news reports quoting them |

## Secrets

No keys are committed: `backend/.env` is ignored and only `.env.example` is tracked. Recorded replay files contain public API responses only.

## Not verified

- No deployment URL yet (Dockerfile and compose file provided and the production build was tested locally).
- No Lighthouse score recorded.
- Not tested on a physical phone; mobile checked with Chrome device emulation (390×844, 360×780).
- The anti-slop Delivery Gate was not run (skills not installed, see DECISIONS.md).
