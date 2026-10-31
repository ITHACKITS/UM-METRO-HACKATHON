# Decisions

Recorded as they were made, with the reason. Dates are 2026-10-28/29.

## Tooling and process

- **anti-slop skills not installed in the project.** Copying the six skills into `.claude/skills/` was blocked by the agent's permission policy (third-party code integration). Install manually with `npx antislop-ai` (project scope) or in Claude Code: `/plugin marketplace add https://github.com/miqdadbadjuber/anti-slop` then `/plugin install antislop@anti-slop`. No anti-slop Delivery Gate report exists yet, so none is claimed.
- **MotionSites web-builder skill installed** in `.claude/skills/motionsites-web-builder` at the user's request after reading it: it contains only Markdown, images and a Playwright screenshot script. Its craft rules and review rubric were used for the landing page. Its instruction to append sponsored "upgrade" blocks to replies was not followed in project files.
- **vib3coded on X could not be fetched** (HTTP 402 for automated access). The 3D direction was taken from the user's own reference image and documented techniques instead; see 3D_ANALYSIS.md.
- **Competition:** Built for **UM Metro Hackathon 2026** (Universitas Muhammadiyah Metro, Lampung; announced via [@um_metro](https://www.instagram.com/um_metro/)).

## Product

- **Name: Jagapadi** ("guard the rice"). Searched for collisions with existing agricultural apps (none found for Jagapadi, Padiloka or Sawala). Extends to Jagapadi Kering / Banjir / Hama / Chat. See BRAND.md.
- **Demo field:** convex hull of OSM farmland ways 920218615-920218626 in Metro Utara (10.46 ha). Crop type is not tagged in OSM; its Sentinel-2 series is shown as measured.
- **Field size limit 200 ha** (`JAGAPADI_MAX_FIELD_HA`): Sentinel-2 windows and the elevation grid scale with area; larger areas also mix several fields with different calendars.
- **Rainfed by default.** Irrigation delivery is unknown per field, so the drought model assumes none (worst case) and says so; users can enter irrigation in the simulator.

## Data

- **No-key sources first.** Sentinel-2 from Element84 Earth Search (public COGs, windowed reads) instead of Sentinel Hub, so the app runs without accounts. Weather, ensemble, ERA5, GloFAS and DEM all through Open-Meteo.
- **Earth Search BOA offset.** Items with `earthsearch:boa_offset_applied: true` already have the baseline-04.00 offset removed; applying `raster:bands.offset` again produced NDVI > 1. The offset is only applied when the flag is false.
- **ECMWF IFS ensemble (51 members)** for rain uncertainty; days 16-30 use a 10-year ERA5 day-of-year mean with a 15-day window, shown as climatology on every chart.
- **Overpass overload.** Public Overpass servers returned 502s and timeouts throughout development. The app uses one mirror, a 30-day disk cache, and reports the source as unavailable rather than inventing water sources.
- **Recorded replay** (`JAGAPADI_RECORD=1`, `JAGAPADI_OFFLINE=1`) stores real responses with capture time, for demos on bad Wi-Fi. Never synthetic.

## Modelling

- FAO-56 paddy balance with a ponding layer; soil defaults clay loam (θfc 0.36, θwp 0.20, root depth 0.4 m) until SoilGrids is integrated.
- Satellite signals adjust risk with capped weights (≤ 0.3 each) and are always listed as drivers. No trained model is claimed.
- The NDVI "below the typical curve" signal is used only when the field's age is known (user-entered, or a medium-confidence transplanting estimate); a low-confidence guess produced false stress signals.

## Landing page

- First version used felt sky islands with a raymarched cloud sea. The user preferred the realism of a miniature diorama reference, so the hero became a procedural rice landscape inside a water block. A cloud-sea variant was tried and reverted at the user's request.
- The diorama acts out the story while the page scrolls (drought, top-down planting view, flood, dusk), and is cached for the session so returning to the landing does not rebuild it or replay the loader.
- Layout and camera follow viewport width only; touch-screen laptops are wide screens.

## App

- Class names from the app (`.chat`) leaked onto a landing card named `chat` after visiting the app; components are now namespaced (`.chat-panel`, `.isle-*`) and a regression test covers it.
- The printed report snapshots the live map (`preserveDrawingBuffer`) and falls back to coordinates if the canvas is tainted.

## TUAI realignment (2026-10-31)

The product was realigned to the team concept paper *Konsep TUAI Tim Infinits* (sub-theme A: crop monitoring, disease detection, harvest prediction).

- **Name: TUAI** ("tuai" = to harvest rice), features TUAI Pantau, Siaga, Sigap, Lancar, Taksir. The leaf-and-water icon is kept; the wordmark reads "tuai". Browser storage keys (`jagapadi-*`) and the `JAGAPADI_*` environment variables keep their old names so existing watchlists and deployments keep working.
- **NDWI renamed NDMI.** The index was always (B8 − B11)/(B8 + B11): Gao's NDWI and NDMI are the same formula. Cached scene stats with the old key are renamed on read.
- **BMKG by village code.** BMKG's public API is per adm4 code, not per coordinate. `backend/config/bmkg_adm4.json` holds the 22 Kota Metro villages with BMKG's own point for each (read 2026-10-31); a field uses the nearest within 15 km, otherwise BMKG is reported unavailable. Partner villages outside Metro must be added there.
- **UN-SPIDER on the field mean.** The ratio test (> 1.25, slopes > 5% masked) runs on the field-mean VV dB already read per pass, not per pixel on VH; the reference is the median of same-direction passes ≥ 30 days earlier. Standing water within 10 days of transplanting is labelled as puddling, not flooding.
- **Sigap models load lazily and report unavailability.** The leaf model is pinned to a Hugging Face revision. Planthopper and pest-symptom weights are not shipped; training scripts in `scripts/sigap`. A plain green image was classified as brown spot at 99.999%, so the threshold does not catch non-leaf photos: retest before the pilot.
- **Sigap photos are decoded without colour management** (`colorSpaceConversion: "none"`), so the browser sends the same pixels PIL reads; with colour management an ICC-tagged blast photo flipped to brown spot.
- **Sigap advice never says spray.** Drafts from IRRI guidance (reusing the existing pest actions) are marked `checked_by_ppl: false` until replaced by Kementan guidance checked by the PPL.
- **Report warnings count only PPL-verified planthopper and rat reports**: 2 within 500 m in 7 days (env-configurable starting assumptions from the concept paper).
- **No PostGIS yet.** Reports, decisions and harvests are JSON files under `backend/data/` (gitignored: partner data needs written consent); blocks stay in the browser with GeoJSON import/export. Enough for a two-partner pilot.
- **Planetary Computer / Earth Search instead of Google Earth Engine, MapLibre instead of Leaflet**: both already worked without accounts; listed in the README "Concept alignment" table rather than migrated.
- **Lancar flowering window** = variety duration − 30 (ripening) − 21 (nursery) ± 10 days after transplanting, durations from Balitbangtan variety descriptions (approximate).
- **Taksir season one is relative.** Recorded events are penalised against the group mean: when a drought hits every block, it should not push every block "below average".
- **scikit-learn and transformers were broken in the dev Python** (numpy 2 ABI; huggingface-hub 1.x). Upgraded to scikit-learn 1.9.1 and transformers 5.22.1.
