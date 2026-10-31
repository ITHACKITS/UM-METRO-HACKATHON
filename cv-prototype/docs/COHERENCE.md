# Coherence across the TUAI prototypes

The two applications should feel like sibling instruments in one field kit. Runtime
independence protects the tested weather/satellite application and its lightweight
dependencies; it does not authorize a second brand or a conflicting product language.

## Shared contract

| Area | Existing field prototype | CV prototype rule |
|---|---|---|
| Product voice | Indonesian-first, plain language, honest unavailable states | Same voice; model result is always an `indikasi model` |
| User escalation | BMKG/PPL/BPBD according to decision | PPL/agronomist for visual confirmation |
| Frontend | React 18, TypeScript, Vite, responsive web | Same family and React version; phone-first capture flow |
| Backend | Python, FastAPI, Pydantic | Same process; isolated Sigap modules and versioned `/api/sigap/v1` namespace |
| Brand | TUAI rice/water mark and lowercase serif wordmark | Same root-shell asset and proportions |
| Surface | warm paper and pressed felt | same paper, fibre, stitch, radius and shadow language |
| Primary action | teal scarf colour | same teal, pill shape and focus behavior |
| State colour | sage/green enough, grain/gold watch, orange act, blue water | same meanings; `abstain` uses grain and `retake` uses drought orange |
| Typography | Instrument Serif accent + Manrope body | same roles and fallbacks |
| Accessibility | mobile targets, visible focus, reduced motion | same, with explicit 360 px acceptance |
| Evidence | source and time, no invented numbers | model ID/revision/hash, raw model-score wording, no invented metrics |

## Deliberately separate evidence contract

- One canonical runtime: web `5173`, API `8000`; Sigap is mounted at `/sigap` and
  `/api/sigap/v1`.
- Sigap source remains isolated under `frontend/src/sigap/`, `backend/app/sigap/`, and
  `backend/tests/sigap/`; scientific assets remain under `cv-prototype/`.
- Existing `forecast_suitability` is environmental evidence; CV
  `visual_observation` is evidence from one photo.
- The existing app may cache field analysis and manage field workflows. Sigap may keep
  up to 20 text-only observation summaries in the current browser; it stores no photo,
  account, exact location, or field link.
- Existing weather routes keep their behavior.
- CV keeps a versioned `/api/sigap/v1` contract because its
  model/provenance/abstention policy must remain explicit.

## Why a web UI instead of native Kotlin in v1

The chosen product is a mobile **web** experience backed by the demo laptop, not an
Android-only application. It can invoke a rear phone camera without installation, works
on Android/iOS/desktop, reuses the existing TUAI frontend skill set, and leaves the
372 MB disease model in Python's mature PyTorch/Transformers runtime. Kotlin would add a
second UI architecture and require either the same Python server or a separately
converted, quantized and device-validated on-device runtime before field accuracy is
known.

A Kotlin client remains a valid later delivery option when requirements demand an APK,
fully on-device operation, background/native APIs, or Play Store distribution. It
should first consume the stable `/api/sigap/v1` policy, then move inference on-device only
after model-size, latency, memory, thermal, score-drift and licence tests.

## Future integration rule

An authorized integration may place both evidence channels on one field screen, but it
must label the source and timestamp of each and keep them side by side. Do not multiply,
average, overwrite, or silently “confirm” them. Extracting a shared component/design
package would modify the existing application and therefore requires explicit user
approval first.

