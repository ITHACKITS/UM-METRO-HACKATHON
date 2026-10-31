# What we learned from HELALOKA (JOINTS2026)

Source: github.com/nyarikerja/JOINTS2026 README, read 2026-10-28. Logic and clarity were studied; no UI, colours, components or code were copied.

## How its simulator works

- One Lagrangian particle engine (RK2 midpoint advection plus random turbulent diffusion) serves volcanic ash and wildfire smoke; source terms from Mastin et al. (2009) for eruption rate and FRP-based smoke emission.
- Rain washout as a power law of rainfall intensity.
- Weather ensembles (15 members, 51 for one volcano): each grid cell's probability comes from all members; impacts are always P5 / P50 / P95, never one number.
- Tiered fallbacks per hazard, and the tier used is shown (live reports → history → catalogue → assumption).
- "Real conditions" vs "Test scenario" modes; test results are labelled hypothetical.
- A time player H+0 to H+48 with probability contours at 90/50/5%.
- `GET /validation/{event_id}` scores only runs actually executed; untestable cases are marked `not_testable`.

## Layout idea

Header with status and clock, a control dock (hazard, place, mode, run, print), a map workspace with layers and a time player, and an analytics drawer with tabs (area, facilities, protocol + AI).

## What TUAI (then Jagapadi) took (adapted to rice)

| HELALOKA idea | TUAI version |
|---|---|
| Ensemble members → P5/P50/P95 | The paddy water balance runs once per ECMWF member (51); first-stress day and submergence days as P5/P50/P95; daily probabilities |
| Real vs test mode | Kondisi nyata / Uji skenario; hypothetical stamp on screen and on the printed report |
| Tiered fallbacks, tier shown | Ensemble → deterministic forecast; recent clear scene → no ponding assumption; live → recorded replay; LLM → templates. Each basis is listed under "Karena" |
| Time player | 30-day day player with a daily risk heat strip; the field recolours by stress or depth |
| `not_testable` honesty | `/api/validation` reports a model consistency check and marks event skill not testable |
| Analytics drawer + print summary | Tabbed drawer (Summary, Drought, Flood, Pests, Water, Data) and an A4 field report |

## Symbols

Hazard glyphs are simple filled shapes readable at 20 px (sun over cracked ground, drop over waves, insect, speech bubble). Map colours encode one variable at a time with a legend that changes with the active tab: stress (green / gold / orange) or water depth (green / light blue / blue / deep blue). Water sources are blue lines or points; the route to the chosen source is a dotted cream line.
