# TUAI design direction

(Written when the product was called Jagapadi; the design direction is unchanged.)

This file gives direction; quality filters (anti-slop) remove what does not belong.

## Idea

A rice field you can hold: the landing page is a hand-made miniature of a Lampung rice landscape inside a block of water, sitting on warm paper. The app is the same world seen as a working tool: calm, legible outdoors on a phone, every number traceable.

## Palette (from the mascot photographs)

| Token | Value | Use |
|---|---|---|
| `--paper` | `#f4ead9` | page, cards |
| `--ink` | `#1b2a23` | text |
| `--teal` | `#1c868b` | the one accent: primary actions, active state (Si Padi's scarf) |
| `--sage` | `#7fa35b` | healthy rice, "enough water" |
| `--grain` | `#e2a93b` | panicles, ripening, "stress starting" |
| `--drought` | `#c4571e` | severe drought, high risk |
| `--flood` | `#1f6fa8` | flood |
| `--button` | `#f3e6c4` | felt button details |

Risk colours mean the same thing everywhere: green enough, gold watch, orange act; blue for water depth.

## Type

Instrument Serif italic for one accent phrase per heading; Manrope for everything else. Display 400-500 weight, tight tracking (−0.04em); body 15-16 px; tabular numerals on data.

## Material

One surface: pressed felt. Cards use `.felt` (matte paper fill, a dashed stitch line inset 7 px, a faint fibre texture). Buttons are pills. Grain overlay at 7% unifies 3D and UI.

## Mascot rules

- Si Padi is a needle-felted rice plant with a teal knitted scarf and cream button.
- Waving pose: welcome, empty states, final call to action. Laptop pose: loading, "how it works", reading data.
- Never recolour the scarf, never crop the panicles, keep at least 16 px clear space, always on paper or light backgrounds (transparent PNGs in `frontend/public/mascot`).

## Motion

- Entrance: blur-rise, 0.9 s, `cubic-bezier(0.22,1,0.36,1)`, 120 ms stagger.
- Scroll story: the diorama is pinned; each chapter glides the camera (lerped) and changes water level, growth stage and time of day to act out the chapter.
- Parallax: paper contours (slowest), diorama, copy, foreground rice stalks (fastest).
- `prefers-reduced-motion`: no parallax, no camera glides, final states only.

## 3D approach

Procedural, no model files: heightfield terrain with terraced paddies, instanced rice and tree blobs, merged village geometry, water rendered from real thickness (Beer-Lambert) with refraction, Fresnel and foam. See docs/3D_ANALYSIS.md.
