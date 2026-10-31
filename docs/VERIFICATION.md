# Verification

Last run on 2026-10-31 after the TUAI realignment, Windows 11, Chrome (ANGLE D3D11), Python 3.12, Node 24. Earlier run 2026-10-29 (25 unit, 63 end-to-end).

## Automated

| Check | Command | Result |
|---|---|---|
| Backend unit tests | `cd backend && python -m pytest -q` | 40 passed (25 earlier + 15 TUAI: BMKG, Siaga, soil, Lancar, Taksir, Sigap) |
| Lint | `ruff check app tests` | All checks passed |
| Type check + production build | `cd frontend && npm run build` | built, no type errors |
| End-to-end | `python scripts/qa.py http://localhost:5173 <dir>` | 72 checks passed, 0 console errors, 0 failed same-origin requests (one earlier run timed out waiting for the LLM chatbot; passed on rerun) |
| Production serving | API on :8010 with built `frontend/dist`, `JAGAPADI_OFFLINE=1` | `/`, `/app`, `/ppl`, `/api/health`, `/api/demo-group` HTTP 200; `/api/verdict` answers from recordings |

The end-to-end suite covers: landing loader and diorama frames; dock water modes, stage, hour; language switch; anchor navigation; stat citation links; credits; 404; no-WebGL fallback; reduced motion; app empty state; a rejected tiny field; demo analysis; farmer verdict, reason and action; tabs hidden in the farmer view; plain-word player; Telegram button hidden without a bot; watch button; expert view; all six tabs; Indonesian drivers; day slider and player; basemap switch; water tab honesty when OSM is down; crop-age edit; scenario mode and its hypothetical banner; back to real; chatbot answers with numbers and sources; pest answer; Escape closes chat; return to landing without loader replay or style leaks; officer dashboard (watched field listed, empty state, sample group of five, tally, risk order, map, opening a plot); block details saved; TUAI Lancar ranks five blocks in order; TUAI Taksir rates five blocks; TUAI Sigap photo analysis, review flag, report sent from a map location, rat form, PPL queue and rejection; 360 px mobile farmer verdict, overflow, tabs and tap targets.

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
| SoilGrids down (HTTP 503 on 2026-10-31) | Lancar uses the clay-loam default and shows the reason per block |
| Sigap model packages missing or weights not trained | Each model reported as unavailable with the reason; the rest of the result still shows |
| Field outside the BMKG village table | BMKG listed as unavailable with the nearest village and distance |

## Numbers traced to source (demo field, 2026-10-28/29)

| Shown | Source / calculation |
|---|---|
| Area 10.46 ha | geodesic area of the OSM-derived polygon (pyproj) |
| NDVI 0.32, NDMI −0.02 on 2026-10-18 | Sentinel-2 L2A scene S2C_48MWV_20261018, SCL-masked field pixels |
| Soil moisture 0.277 m³/m³ | Open-Meteo `soil_moisture_9_to_27cm`, current hour |
| Last 30 days rain vs normal | Open-Meteo past days vs ERA5 2016-2026 day-of-year mean |
| 51 members | ECMWF IFS 0.25° ensemble via Open-Meteo |
| 2-year flow 8.38 m³/s | Gumbel fit to 21 years of GloFAS annual maxima at the field's grid point |
| Field 43 m elevation, 6% surroundings lower | Copernicus DEM GLO-90 9×9 grid via Open-Meteo |
| Drought % and first-stress day | FAO-56 balance per ensemble member (see README method) |
| Pest levels | favourable-day counts over the last and next 7 days of Open-Meteo weather |
| Problem statistics on the landing | Pusdatin Kementan 2024 and Prasetyo & Kadir 2023, as cited in the team concept paper |
| BMKG forecast (Yosodadi, 2026-10-31..11-02: 4.1, 0.8, 2.9 mm) | `api.bmkg.go.id` adm4 18.72.04.1001, the nearest of 22 Kota Metro villages, 3-hourly `tp` summed per day |
| Radar flood ratio ≈ 1.0 (not flooded) | field-mean VV dB / median of same-direction passes ≥ 30 days earlier |
| Sigap: blast 83%, brown spot 93% | `prithivMLmods/Rice-Leaf-Disease` on two Wikimedia Commons photos (not stored in the repo) |
| Lancar 7-day need ≈ 24 mm per block | Σ ET0·Kc + percolation − median ensemble rain − ponding |

## Secrets

No keys are committed: `backend/.env` is ignored and only `.env.example` is tracked. Recorded replay files contain public API responses only.

## Not verified

- No deployment URL yet (Dockerfile, compose file and `render.yaml` provided; production serving tested locally). The Docker image itself was not built here because Docker Desktop was not running.
- Si Padi verified live on Gemini (free tier): field_summary, drought_outlook, pest_outlook and run_scenario tool calls answered from the field data.
- No live Telegram bot (no token). The alert flow is covered by unit tests with a fake sender: linking, reuse refused, morning round, one all-clear, stop.
- No Lighthouse score recorded.
- **Sigap leaf model on field photos: not tested.** On two openly licensed photos it was right; on a plain green square it said brown spot at 99.999%, and the synthetic QA image (green ellipse) came back as kresek 89%. Retest with `scripts/sigap/eval_disease.py` before the pilot.
- **Colour management changed the leaf result.** Through the browser, the same blast photo (with an ICC profile) first came back as brown spot 53%: the canvas applied colour management, the model was trained on unmanaged pixels. Fixed by decoding with `createImageBitmap(..., { colorSpaceConversion: "none" })`; the page now matches the API (blast 83%). It also shows how sensitive the model is to small colour shifts.
- **Planthopper detector and pest-symptom classifier: not trained**, so not tested. Roboflow hosted mode not tested (no key).
- **Taksir regression path** tested only with synthetic records in unit tests; no real harvest data yet.
- Lancar and Taksir results are not checked against a P3A chair's judgement yet (concept target: ≥ 80% of blocks match).
- Not tested on a physical phone; mobile checked with Chrome device emulation (390×844, 360×780).
- The anti-slop Delivery Gate was not run (skills not installed, see DECISIONS.md).
