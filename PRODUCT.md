# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are Indonesian rice farmers using a phone in the field. Agricultural extension workers (PPL) review observations and help interpret safe next actions. Hackathon judges, researchers, and the project team also need a clear evidence trail and an understandable demonstration.

## Product Purpose

TUAI helps users monitor rice fields through satellite and weather information, screen visible rice-leaf symptoms and supported pests from photos, and make safer follow-up decisions. Success means a first-time user can complete the relevant task on a phone, understand what the result does and does not mean, and know the next responsible action.

## Positioning

TUAI keeps forecast-based field suitability and direct visual observations as separate evidence types while presenting them in one coherent agricultural workflow.

## Operating Context

The product is used on phones and tablets in farms and field visits, with laptop support for demonstrations and review. Connectivity can be unreliable. Photo capture happens under variable light and backgrounds. The hackathon demonstration must remain usable after model preparation with the network disabled.

## Capabilities and Constraints

- TUAI Pantau, Siaga, Sigap, Lancar, and Taksir form the broader product concept; the interface must distinguish implemented capabilities from roadmap concepts.
- The current production prototype provides satellite and weather monitoring. Its environmental pest signal is weather suitability, not visual pest detection.
- TUAI Sigap accepts an explicit disease or visible-pest mode. It reports an `indikasi model`, never a definitive diagnosis.
- Disease and pest pipelines remain separate and use different capture guidance.
- Outputs may abstain or request a retake. A negative pest result never means the plant is safe.
- V1 does not estimate severity, prescribe pesticides, generate doses, claim presymptomatic detection, store uploaded photos, or associate observations with a field block or account.
- Model performance claims require an immutable evaluation manifest and aggregate report. Published model-card metrics are not TUAI accuracy.
- Visual-observation evidence must never be silently fused with forecast-suitability scores.

## Brand Commitments

The product name is TUAI: Sistem Pertanian Cerdas Berbasis Citra Satelit dan Computer Vision untuk Monitoring Kondisi Padi, Deteksi Penyakit dan Hama, serta Prediksi Hasil Panen. The interface is Indonesian-first, practical, calm, and honest. It should feel recognizably connected to Indonesian rice farming without becoming a decorative agricultural costume. Existing TUAI/Jagapadi field imagery, mascot assets, and the established teal, grain, drought, and flood semantics may be retained when they improve comprehension. The user must approve the design direction before implementation is visually frozen.

For TUAI Sigap, that approval is now complete. The locked screen directions are Bengkel Foto for capture and photo-quality preflight, Jendela Tugas for direct camera and task-specific framing, Foto dan Bukti for results, and Dua Jalur for local disease/pest history. Use warm paper, deep ink, accessible dark teal, restrained rules/corners, Manrope working text, and the existing TUAI mark. Avoid generic marketing heroes, repeated floating cards, glass effects, gradients, excessive pills, eyebrow labels, ornamental tiny text, and decorative imagery that does not help the field task. Do not generate images for Sigap unless the user explicitly reverses the current prohibition.

Visual coherence does not authorize edits to the other prototype. Work stays inside isolated Sigap/CV paths unless the user grants new permission.

## Evidence on Hand

- Existing satellite/weather application and representative UI in `frontend/`.
- Integrated Sigap frontend in `frontend/src/sigap/` and backend in `backend/app/sigap/`.
- Research, model provenance, evaluation plans, and validation constraints in `cv-prototype/docs/`.
- Hackathon and product context in `CONTEXT.md`, `HACKATHON_AGENT_PROMPT.md`, and the supplied TUAI concept documents.
- No completed local expert validation, farmer testimonial, or independently measured model accuracy may be fabricated.

## Product Principles

1. Show the evidence type and its limits before asking the user to trust a result.
2. Prefer a narrow workflow that works in the field over a broad set of untested claims.
3. Make safe next actions clearer than model scores.
4. Keep local photos private and make saving or sharing an explicit user action.
5. Preserve one coherent TUAI product while keeping technical modules loosely coupled.

## Accessibility & Inclusion

The interface must work at a 360-pixel phone width, support keyboard operation and visible focus, maintain readable contrast and touch targets, respect reduced motion, use plain Indonesian, and avoid relying on color alone. Bilingual technical labels may supplement, but not replace, Indonesian guidance.
