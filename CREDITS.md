# Credits and attribution

## Data

| Source | Licence / terms | Attribution |
|---|---|---|
| Copernicus Sentinel-2 L2A via Element84 Earth Search (AWS Open Data) | Copernicus free and open data policy | Contains modified Copernicus Sentinel data (2026) |
| Open-Meteo (Forecast, Ensemble, Historical, Flood, Elevation APIs) | CC BY 4.0 data; free non-commercial API | Weather data by Open-Meteo.com |
| ECMWF IFS ensemble, ERA5 (through Open-Meteo) | CC BY 4.0 | ECMWF / Copernicus Climate Change Service |
| GloFAS v4 (through Open-Meteo) | CC BY 4.0 | Copernicus Emergency Management Service |
| Copernicus DEM GLO-90 (through Open-Meteo) | Copernicus DEM licence | © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA |
| OpenStreetMap (Overpass API) | ODbL 1.0 | © OpenStreetMap contributors |
| Esri World Imagery | Esri terms of use | Esri, Maxar, Earthstar Geographics, and the GIS User Community |
| Sentinel-2 cloudless 2023 (EOX) | CC BY-NC-SA 4.0 | Sentinel-2 cloudless by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2023) |
| Rice loss figures | Cited news reports of BPS and Kementan releases | Links in README |
| BMKG Prakiraan Cuaca Terbuka (api.bmkg.go.id) | Free; BMKG must be credited | Sumber: BMKG |
| Copernicus Sentinel-1 RTC via Microsoft Planetary Computer | Copernicus free and open data policy | Contains modified Copernicus Sentinel data (2026) |
| ISRIC SoilGrids 2.0 | CC BY 4.0 | ISRIC World Soil Information |
| prithivMLmods/Rice-Leaf-Disease (Hugging Face model) | Apache-2.0 | prithivMLmods; fine-tuned from google/siglip2-base-patch16-224 |
| Roboflow identification-planthopper (training, scripts/sigap) | CC BY 4.0 | S. A. Supriadi, Roboflow Universe |
| IP102 (optional pre-training) | Academic use only | Wu et al., CVPR 2019 |
| Paddy Doctor (pest-symptom training) | No licence stated; ask the authors | Petchiammal et al., CODS-COMAD 2023 |
| UN-SPIDER Recommended Practice, flood mapping with Sentinel-1 | Method cited and rewritten; code licence not stated | UN-SPIDER |
| Problem figures 2024 | Pusdatin Kementan, Statistik Iklim, OPT dan DPI 2024; Prasetyo & Kadir 2023 (MPRA 119446) | Team concept paper |

## Libraries

React, React Router, Vite, TypeScript, Three.js, MapLibre GL JS, GSAP (ScrollTrigger), FastAPI, Uvicorn, httpx, pydantic, numpy, rasterio (GDAL), shapely, pyproj, Anthropic Python SDK, Google Gen AI Python SDK, Playwright (tests), Pillow and SciPy (asset scripts).

## Methods

FAO-56 (Allen et al. 1998), USDA NRCS TR-55 curve number, Gao (1996) NDWI, McFeeters (1996) NDWI, IRRI Rice Knowledge Bank (pest and AWD guidance).

## Artwork and design references

- Mascot Si Padi: artwork supplied by the Jagapadi team.
- Landing diorama: original procedural scene. The "miniature in a water block" presentation was inspired by a reference image the team supplied; no assets or code were copied.
- The app's layout ideas (control dock, map workspace, analysis drawer, real vs test modes, P5/P50/P95 reporting) were studied from HELALOKA (github.com/nyarikerja/JOINTS2026); no UI, code or assets were copied.
- MotionSites web-builder skill used as a design checklist during development.
- Fonts: Instrument Serif and Manrope (SIL Open Font License) via Google Fonts.
