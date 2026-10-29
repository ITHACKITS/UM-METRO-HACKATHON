# Hackathon Agent Prompt: Reusable Template

A master prompt for a coding agent (Claude Code or similar) that builds a complete, real-data, deployable hackathon web app from a short brief. It was written from building **Jagapadi** (rice-field drought, flood and pest monitoring for Metro, Lampung) and keeps every lesson from that build.

## How to use this file

1. Copy this file into the new project's empty repo root.
2. Fill in **Part A: Project brief**. Leave a field as `TBD` if you don't know it yet; the agent asks for it once and keeps working with a labelled placeholder.
3. In **Part C: Feature modules**, delete the modules the project doesn't need.
4. Put your input files (mascot, reference images, logos, data) in the repo root or `assets/`, and list them in A.6.
5. Give the agent this instruction: *"Read HACKATHON_AGENT_PROMPT.md and build the project. Follow the phases in order."*

Part B (rules) and Parts D–F (verification, repo, delivery) apply to every project. Change them only on purpose.

---

# Part A: Project brief (fill this in)

### A.1 Event
- **Hackathon name:** `TBD`
- **Announcement / rules link:** `TBD`
- **Theme and judging criteria:** `TBD` (paste them; the agent shapes the pitch to them)
- **Deadline and demo format:** `TBD` (for example a 3-minute live demo plus a repo link)

### A.2 Team
- **Members and roles:** `TBD`
- **Git author:** `TBD` (commits are made as this user only; see B.6)

### A.3 Problem and users
- **Problem in one sentence:** `TBD`
- **Who has it:** `TBD` (primary user, plus a second user who manages many of them, if there is one)
- **Where:** `TBD` (default demo region, a real place)
- **Why now:** `TBD` (a current, citable reason)

### A.4 Core idea
- **What the app does:** `TBD`
- **Core data signal:** `TBD`
- **Inspiration / competitors:** `TBD`, and what we do that they don't.

### A.5 Look and feel
- **Landing page reference:** `TBD` (image files and links)
- **Texture / material language:** `TBD` (for example needle-felted wool and knitted yarn, matching the mascot)
- **Mascot:** `TBD` (file names, poses, what it must never become)
- **Theme words:** `TBD`

### A.6 Input files in the repo
| File | What it is | Where the agent should move it |
|---|---|---|
| `TBD` | | |

### A.7 Reference repos and sites
| Link | What to learn from it | What NOT to copy |
|---|---|---|
| `TBD` | | |

### A.8 Keys and accounts available
- LLM: `TBD` (Anthropic / Gemini / none). Put keys in `backend/.env` yourself; never paste keys in the chat.
- Other: `TBD` (Telegram bot token, map tokens, etc.)

### A.9 Example brief (Jagapadi, for reference)
- **Problem:** farmers in Lampung lose rice harvests to drought, and learn about it only when the soil cracks. Flood and pests extend the core; drought stays the headline.
- **Users:** farmers and farmer groups (kelompok tani); extension officers (PPL) who advise hundreds of plots.
- **Core signal:** Sentinel-2 NDVI/NDWI and Sentinel-1 radar, plus an ensemble weather forecast and a water balance.
- **Inspiration:** "Harvey" on Devpost (weather + soil, no IoT). Simulator logic from github.com/nyarikerja/JOINTS2026 (logic and symbol clarity only, not its UI).
- **Look:** sky islands with terraced paddies; everything felt and knit like the mascot (a needle-felted rice plant with a teal knitted scarf).

---

# Part B: Operating rules (always apply)

### B.1 Ask vs continue
- Ask the user **only** for what you cannot get or decide yourself: missing input files, keys you cannot create, the event name and judging criteria. Ask **once**, in one message that lists everything missing. Then keep working with a clearly labelled placeholder and swap the real thing in when it arrives.
- Decide everything else yourself. Record each decision and its reason in `docs/DECISIONS.md`, then move on.
- Work in phases (Part C). Finish each phase's acceptance checks before starting the next. Keep a task list.

### B.2 Honesty and data
1. **No dummy data.** Every number shown comes from a live API, a documented dataset, or a deterministic calculation from those. If a source is down or has no coverage, show "not available" and the reason. Never invent values, ratings, statistics, charts or "AI confidence".
2. **Recorded data only if real:** responses captured from the live APIs, stored with their capture time and labelled "recorded on <date>" in the UI.
3. **Show uncertainty:** ranges (P5 / P50 / P95) or risk levels with a stated confidence and the signals behind them.
4. **Not an official warning** (when the domain needs it): a visible disclaimer that names the official bodies (for Indonesian agriculture and disasters: BMKG, PPL, BPBD).
5. **Verify before you claim.** Endpoints, free-tier limits and licences change. Fetch each source's current docs, confirm access and terms, and record the check date in `backend/docs/SOURCES.md`. If you could not verify something, say so.
6. **Do not claim accuracy you did not measure.** Every model output says what it was validated against, what it was not, and whether a simple baseline does as well (see C.4.4).
7. **No dangerous advice from memory.** For example, no pesticide or medicine doses; point to the product label and the qualified local person.

### B.3 Secrets
- Keys live only in `backend/.env`. Commit `.env.example`. Check `.env` is ignored with `git check-ignore backend/.env` before the first commit.
- Never put keys in frontend code, logs, screenshots, test fixtures, recordings or git history. Before release search history: `git log -p | grep -iE "api[_-]?key|token|secret|AIza|sk-"`.
- Runtime user data (chat IDs, subscriptions, uploads) goes in a gitignored `backend/data/` folder.
- If the user pastes a key in the chat, use it only to write `.env`, and remind them to rotate it after the event.

### B.4 Priority when time runs short
Build a thin vertical slice first, then widen:
1. Landing page with the mascot and hero scene (first impression).
2. One real input (for example one field) analysed end to end with real data.
3. The headline prediction with its explanation and recommendations.
4. The simple user view (one verdict, one action).
5. Second and third predictions.
6. Grounded chatbot with the mascot.
7. Alerts, the manager / group view, printable report, extras.
8. Deployment, README, screenshots, pitch and demo script. **Never skip; reserve time.**

Never leave a half-built feature visible. Hide it and list it under "Not finished" in the final report.

### B.5 Pinned stack (change only with a recorded reason)
- **Backend:** Python 3.10+, FastAPI, httpx, pydantic, numpy, pytest, ruff. File caches on disk; SQLite only when queries need it.
- **Frontend:** React + TypeScript + Vite. MapLibre GL for maps. Three.js (or React Three Fiber) + GSAP ScrollTrigger + Lenis for a 3D landing.
- **E2E:** Playwright (Python) script `scripts/qa.py`, and a screenshot script `scripts/capture.py`.
- **Deploy:** one Dockerfile (build the frontend, serve it from the backend) plus `render.yaml` (Render free plan) or a Railway / Fly config.
- **LLM:** provider-agnostic (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`) with a deterministic template fallback when no key is set (see C.6).
- **Dev runner:** root `package.json` with `npm run dev` that starts **both** API and web. Running only the web server leaves every API button dead.

### B.6 Git
- Commit at the end of each phase with a plain message that says what changed.
- **Do not add AI co-author or "Generated with" lines** to commits or PRs. Commits belong to the team's git user only.
- Never force-push or rewrite pushed history without the user's explicit go-ahead.

### B.7 Machine quirks (Windows)
- `uvicorn --reload` often misses edits on Windows. Restart the API after backend changes before you test.
- Use forward slashes in scripts; write text files as UTF-8.

---

# Part C: Phases and feature modules

## Phase 0: Setup and design direction

1. **Anti-slop skills (optional):** if the brief names a skill pack (for example github.com/miqdadbadjuber/anti-slop), read its README, install it at project scope, and prove it worked: list the skill folders, each with a `SKILL.md`. If installing fails, record that in `DECISIONS.md` and continue; apply the same intent by hand: no sparkle logos, "beta" pills, fake terminals, invented metrics or emoji bullets; plain, concrete copy; real states for empty, loading and error.
2. Write **`DESIGN.md`** at the repo root: palette as HSL tokens, type scale, texture language, mascot usage rules, motion language, 3D approach, icon style.
3. Move the input files to their homes (A.6). Create `docs/DECISIONS.md`.

**Acceptance:** `DESIGN.md` written; inputs moved; decisions log started.

## Phase 1: Brand

1. **Name:** shortlist five short, pronounceable names that extend into sub-brands (`<Name> Drought`, `<Name> Chat`). Check GitHub, npm, domain and social handles as far as you can verify, and check the name doesn't collide with an existing product in the field. Choose one and justify it in `docs/BRAND.md`.
2. **Logo:** SVG, legible at 16 px, in the mascot's material language. Deliver the primary lockup, a **dark-mode lockup** (light text), monochrome, icon-only, a favicon set and an OG image.
3. **Mascot to transparent PNG:**
   - Use an AI matting model, not a colour key, when the background colour is close to the subject: `pip install rembg onnxruntime`, then `remove(img, session=new_session("isnet-general-use"), alpha_matting=True)`.
   - Check the result **composited on a dark background** to see halos or leftover background. Redo it if you see either.
   - Export the full figure (1024 px max) plus 64, 128, 256 and 512 px with `@2x`, and **square avatar crops** at 64, 128 and 256 px.
   - Crop the avatar tight on the face. A full-body crop reads as a blob at 44–52 px.
   - Put the files in `frontend/public/mascot/`. Use them in the landing page, the chatbot button and header, the loader, empty states and the 404 page.
4. **README logo in dark mode:** use a `<picture>` element with a `prefers-color-scheme: dark` source.

**Acceptance:** `docs/BRAND.md`, logo set, mascot set, favicon wired; every page loads with no broken image requests.

## Phase 2: Landing page

1. **Reference study:** fetch each reference link. Social sites (X, Instagram) usually block automated fetching: record that, ask once for screenshots, and continue with well-documented techniques. Write `docs/3D_ANALYSIS.md`: camera, layering, shaders, lighting, post-processing, scroll choreography and performance, marking what you **observed** separately from what you **inferred**. Never copy a creator's scene, assets or code.
2. **Effects:** layered parallax (scroll and pointer), the hero scene from A.5, atmospheric perspective, materials matching the mascot (procedural fibre and knit textures to keep the page light), and a themed loader.
3. **Story sections** that tie the scene to the problem, with real cited figures only.
4. **Budget and fallbacks:** interactive in about 3 s on a mid-range phone; 60 fps on desktop; lazy-loaded 3D; compressed textures; a static fallback when WebGL 2 is missing; a `prefers-reduced-motion` path; no layout shift; fewer layers on mobile.

**Acceptance:** desktop and 360 px screenshots; reduced-motion and no-WebGL fallbacks checked; Lighthouse recorded (or listed as not run).

## Phase 3: Data layer (everything real)

1. One ingest module per source in `backend/app/ingest/`, with typed schemas, TTL caching, retries with backoff, and rate-limit awareness. A per-source status goes on `GET /api/health`.
2. **Prefer no-key sources** so the app runs without signups; add keyed sources as optional upgrades.
3. **Shared HTTP layer** (`ingest/http.py`): one client with retries, a `SourceUnavailable` exception, disk caching, and **record/replay**:
   - `JAGAPADI_OFFLINE=1`-style switch (`<APP>_OFFLINE`) replays recorded real responses.
   - Make replay **date-agnostic**: store each recording under its exact key and under a key with the dates blanked, so a recording from yesterday still answers today's request. Show the capture time in the UI.
   - Do a recording pass over the demo inputs before the event.
4. **Circuit breakers** for flaky public APIs (for example Overpass): after a failure, skip that source for about 10 minutes with short timeouts, and report it as unavailable instead of hanging the whole analysis.
5. **Caches:** cache heavy reads (for example satellite pixel tiles snapped to a grid) in a gitignored `data/` folder, written atomically. Confirm cached and uncached results are identical.
6. **Input limits:** set and record a maximum input size (for example field area) so analysis stays fast and within API limits; reject tiny or invalid inputs with a message.
7. **Docs:** every source, its update frequency, licence, rate limit and check date go in `backend/docs/SOURCES.md` and the README; attributions go in `CREDITS.md`.

Sources used by Jagapadi (reuse for any geo / agri / climate project):

| Need | Source (key?) |
|---|---|
| Weather, forecast, ensemble (51 members), soil moisture, ET0, elevation | Open-Meteo (no key), ECMWF IFS ensemble, ERA5 archive |
| River discharge and flood outlook | Open-Meteo Flood API (GloFAS) |
| Optical vegetation (NDVI, NDWI, SCL cloud mask) | Sentinel-2 L2A via Planetary Computer or Element84 Earth Search STAC (no key), reading COG windows for the area only |
| Cloud-proof water | Sentinel-1 RTC via Planetary Computer (anonymous SAS token) |
| Water bodies, farmland polygons | OpenStreetMap via Overpass; OSM API v0.6 as a fallback when Overpass is down |
| Climate indices for validation | NOAA PSL (ONI, DMI) |
| Basemap | Esri World Imagery, Sentinel-2 cloudless |

## Phase 4: Core analysis and prediction

### C.4.1 Physics / math core (deterministic, explainable)
- Model the process with established, cited methods (Jagapadi: FAO-56 daily water balance with crop coefficient by growth stage; rainfall-runoff and DEM indices for flood; weather-driven favourable-day counts for pests).
- Run it across **ensemble members** and report P5 / P50 / P95 plus probabilities and the first day a threshold is crossed.

### C.4.2 Imagery / AI layer
- Say plainly whether it is **trained** or **training-free**. If training-free (rules on NDVI/NDWI curves, neighbour comparison), say so in the code docstring, README and UI, and never present it as a learned model with an accuracy.
- Imagery feeds the physics core (initial state, crop stage, anomaly signals), and the UI shows which scene, its date and its age. Never present an old scene as current.

### C.4.3 Fusion and explanation
- Merge physics outputs and imagery signals into one risk with a stated confidence. Show the drivers ("12 days of rain deficit, NDVI 18% below neighbours, low soil moisture").
- Lower confidence when inputs are old, missing or unreliable, and say why.

### C.4.4 Validation (be honest)
- Expose `POST /api/validation` (or similar) and a "Validation and limitations" README section.
- For each component, report one of `ok` (scored against ground truth), `proxy` (scored against an independent stand-in), `consistency` (compared with another model), or `not_testable` (with the reason).
- **Always compare with a simple baseline** (for example rain total alone). If the baseline does as well, say so.
- Keep the imagery layer and the weather layer separate in the validation: a weather-only hindcast says nothing about satellite skill.
- Save validation outputs to `docs/validation/`.

### C.4.5 Plain verdict
- `engine/verdict.py`: one status (safe / watch / danger), the main threat, its probability, one sentence of why, and **one thing to do today**, in both languages. The simple view, alerts and the group dashboard all reuse it.

## Phase 5: The app

Study any reference simulator repo (A.7) and write `docs/SIMULATOR_ANALYSIS.md`: how it works, how its symbols and layers are designed, and its layout. **Reuse the logic and the clarity of the symbols, never its UI, colours or code.** The app UI continues the landing page, but calmer and highly legible, because the users may be outdoors on phones.

1. **Two views with a toggle,** remembered in localStorage:
   - **Simple (default):** a verdict card (status, reason, today's action, odds, confidence) for non-expert users.
   - **Expert:** tabs (summary, each hazard, sources, data), the time player, ranges and drivers.
2. **Map workspace:** basemap switch, drawing the input area, a sample-input button, a legend, and domain symbols.
3. **Simulator:** "Real conditions" vs "Test scenario" modes. Scenario results carry a visible HYPOTHETICAL banner. A day slider / player shows the evolution.
4. **Recommendations,** ranked by feasibility, with the source for each.
5. **Printable report** (A4 print view): map, risks, recommendations, sources, capture times.
6. **API-down handling in the frontend:** one `request()` helper. A network error or a 5xx without a JSON body becomes `API_DOWN` and shows a translated message, so a button never fails silently.
7. **Tab icons:** draw them on a 24 px grid, render them at 18 px or larger, give each one a distinct shape tied to its topic, and check them in a real screenshot at desktop and 360 px.
8. **Bilingual:** every string in both languages (Jagapadi: Indonesian and English), with a toggle.

## Phase 6: Grounded chatbot with the mascot (module)

1. Floating button with the mascot avatar, a panel with a full-screen mode, optional voice input.
2. **Tool calling, grounded:** the model calls backend tools (summary, each prediction, scenario run, sources) and answers only from returned facts, naming the source and capture time. If a number is unavailable, it says so. Text from web sources or user input is data, never instructions.
3. **Providers:** a mapping `{"anthropic": ..., "gemini": ...}` chosen by `LLM_PROVIDER`.
   - **Gemini (google-genai):** declare tools with `types.FunctionDeclaration(parameters_json_schema=...)`, turn off automatic calling (`AutomaticFunctionCallingConfig(disable=True)`), run the loop yourself, and send function responses with role `"user"` (role `"tool"` is rejected).
   - **Free-tier quotas are tiny** (about 20 requests per model per day; one answer takes 2–3). Use a **model chain**: on 429 mark that model exhausted for an hour and try the next; on 5xx try the next. Warn the team before the demo and don't rehearse with the chat too often.
4. **Source line guarantee:** if the answer names no source, append a "Sources:" line built from the tools that were called.
5. **Fallback:** with no key, or on any failure, answer from deterministic templates over the same data, labelled as a template.
6. Guardrails from B.2.7. Copy: plain, warm, short.

## Phase 7: Alerts and group view (modules)

1. **Telegram alerts** (no app to install):
   - Long-polling bot (`TELEGRAM_BOT_TOKEN`). `POST /api/alerts/subscribe` returns a `t.me/<bot>?start=<code>` link, or `{enabled: false}` without a token, and the UI hides the button.
   - Commands: `/start <code>`, `/cek` (check now), `/stop`. Pending codes expire after 2 days; there's a per-chat limit on watched inputs.
   - A morning round at a configured hour sends only while the risk is up, plus one all-clear. A last-round marker on disk prevents re-sends after restarts. Run a single worker.
   - Unit-test it with a fake sender.
2. **Manager / group dashboard** (for example the extension officer, `/ppl`): a watchlist in localStorage, "check all" with a small worker pool, a tally by status, a list ranked by risk, a group map, GeoJSON import/export, and a sample group built from **real** data (Jagapadi: 5 real OSM farmland plots in `config/demo_group.json`).

## Phase 8: Extras (only after the essentials are solid)

Pick by impact: an irrigation planner tied to the forecast; a planting-window advisor; an offline PWA caching the last analysis; an evidence report for insurance or aid claims; neighbour comparison; community reports kept visibly separate from model data; an IoT ingest endpoint (per-device token; never show readings that no device sent).

---

# Part D: Verification (do not self-certify without evidence)

Record everything in `docs/VERIFICATION.md` with the date, OS, browser and versions.

| Check | How |
|---|---|
| Unit tests | `cd backend && python -m pytest -q`: paste the pass count |
| Lint | `ruff check app tests` |
| Types + build | `cd frontend && npm run build` |
| End to end | `python scripts/qa.py http://localhost:5173 <outdir>`: every feature clicked, **0 console errors, 0 failed same-origin requests**, desktop and 360 px |
| Production serving | API serving the built `frontend/dist` with offline replay: every route answers 200 |
| Clean clone | follow only the README commands; fix any step that fails |
| Numbers | trace ten displayed numbers to their source or calculation, in a table |
| Failure paths | network off, no LLM key, source down, invalid input, no recent clear image, no WebGL, reduced motion: each degrades honestly |
| Secrets | `git check-ignore backend/.env`; history search from B.3 |
| Not verified | list it plainly (no deploy URL, no physical phone, no Lighthouse, no live bot, and so on) |

**Screenshots:** `scripts/capture.py <url> docs/screenshots <section>` writes straight into `docs/screenshots/`. Re-run it after any visible change so the README never shows an old UI.

---

# Part E: Repository and README

```
<app-name>/
├── README.md / README.id.md     Main docs (English / Indonesian)
├── DESIGN.md                    Design direction
├── CREDITS.md                   Code, assets, data, libraries, mascot ownership (say if AI-generated)
├── LICENSE                      MIT unless the team decides otherwise
├── Dockerfile, docker-compose.yml, render.yaml
├── package.json                 npm run dev starts API + web
├── scripts/                     qa.py, capture.py, asset conversion, recording pass
├── docs/                        DECISIONS, BRAND, 3D_ANALYSIS, SIMULATOR_ANALYSIS, VERIFICATION,
│                                PITCH_DECK, DEMO_SCRIPT, validation/, screenshots/, reference/
├── backend/
│   ├── app/  (main, services, api, ingest, engine, ai, llm, alerts, schemas)
│   ├── config/  data/ (gitignored caches, replay, alerts)  docs/ (API_CONTRACT, SOURCES)
│   ├── tests/
│   └── .env.example
└── frontend/
    ├── public/ (mascot/, logo/, textures/)
    └── src/ (landing/, app/, components/, lib/api.ts)
```

**README order:** logo (`<picture>` with a dark variant) and title, one-line tagline, event name, badges (demo, stack, tests with the real count, licence), quick links, hero screenshot, disclaimer, contents, **Problem** (real cited figures), **Summary**, **Features**, **Screens** (grouped tables with captions that match the image), **Try it in three steps**, **Run locally** (npm, manual, config table, Docker), **Deploy**, **Architecture** (Mermaid), **Scientific method** (with references), **Validation and limitations**, **Data sources**, **API**, **Testing**, **Repository structure**, **Team**, **License and attribution**.

Every link and screenshot must be real. Plain sentences, no filler, no emoji bullets.

---

# Part F: Delivery

### F.1 Definition of done
- [ ] Part D completed with evidence.
- [ ] No invented numbers anywhere (UI, README, chatbot, pitch).
- [ ] Landing page with fallbacks; the simple view and the expert view both work end to end.
- [ ] Validation section states what is measured, against what, and the baseline.
- [ ] Chatbot grounded, cites sources, falls back without a key; mascot avatar sharp at button size.
- [ ] Logo, favicon and mascot wired; no broken requests.
- [ ] 360, 768 and 1280 px checked.
- [ ] Deployed URL works in a clean browser, or "not deployed" is stated.
- [ ] `docs/PITCH_DECK.md` and `docs/DEMO_SCRIPT.md` (3 minutes: problem, live demo, the user's action, the manager's view, the science, honest limits).
- [ ] Pre-demo checklist: recording pass done, offline switch tested, LLM quota left, bot token set, phone ready.

### F.2 Final report (short)
App name and why; live URL; what is live versus recorded; sources you couldn't access or verify; what's unfinished or hidden; files still needed from the user; the three best next steps.
