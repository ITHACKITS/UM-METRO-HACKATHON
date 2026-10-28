# 3D analysis

## References

- **x.com/vib3coded**: not reachable by automated fetch (HTTP 402). Nothing below claims to describe its posts.
- **docs/reference/landing-sky-islands.jpg** (user supplied): floating islands, pink and lavender clouds, waterfalls. Informed the first landing version.
- **docs/reference/image.png** (user supplied): a miniature shrine island in a rounded block of clear water on warm paper, with a detailed prompt describing its pipeline. Observed in the image: heightfield terrain visible through the water's side walls, dense blob-instanced trees, water colour that deepens with thickness, a soft floor shadow, tilt-shift. The prompt's techniques (depth-texture water with Beer-Lambert absorption, refraction, Fresnel, foam, caustics, instanced vegetation, merged architecture, tilt-shift) were reimplemented for an original rice landscape.

## What Jagapadi's diorama does (`frontend/src/landing/Diorama.ts`)

| Part | Technique |
|---|---|
| Terrain | 340² heightfield clipped to a rounded block; hill terraced by quantising height on the side facing the plain; paddy plots and bunds from a rotated grid; river, embung and village terrace carved in; per-vertex horizon AO from 8 directions × 3 radii; skirt shows the soil cross-section |
| Land shader | MeshStandardMaterial extended: cracked dry soil (Voronoi edges) blended by drought amount, wet terraces, mud film after floods, darker wet band above the waterline, animated caustics under water |
| Rice | ~16k instanced tufts of three crossed blades; height and colour driven by growth stage (seedling, green, gold, stubble) and drought; wind sway in the vertex shader |
| Trees | ~3.6k noise-displaced icosphere blobs clustered 2-4 per tree, neighbour-occlusion darkening, brighter tops |
| Architecture | merged vertex-coloured mesh: rumah panggung on stilts with hip roofs, musholla, dangau, sluice gate, footbridge, coconut palms; separate emissive mesh for windows at dusk |
| Water | opaque pass to a HalfFloat target with a depth texture; water pass with a manual depth test; thickness from view-space depth ratios plus a slab test for the box exit; Beer-Lambert absorption toward a scatter colour (muddy in floods); refraction that never samples foreground; Fresnel sky; sun glints; foam where land is shallow; click ripples |
| Light | sun azimuth/elevation/colour from the time slider; golden hour; glowing windows and two point lights at dusk; PCF soft shadows |
| Post | final pass: un-premultiply, ACES tone mapping, sRGB, tilt-shift blur toward top and bottom, alpha kept so the paper shows through |
| Story | `setView` glides the orbit (theta, elevation, distance) and the frame offset per chapter; pointer parallax nudges the camera |

## Performance

- Built in about 2 s on a laptop GPU; 30-60 fps measured at 1440×900 on the development machine (D3D11).
- Narrow screens (≤ 760 px): fewer instances (6k rice, 1.4k trees), smaller shadow map, no MSAA, auto-orbit instead of drag.
- Rendering pauses when the stage is off screen; the built scene is cached for the session.
- Without WebGL 2 the page shows a message and the rest works.

## Earlier version (kept in history)

Felt sky islands with a raymarched cloud sea, shell-textured fuzz, bloom and adaptive quality. Two bugs found and fixed there are worth noting for any WebGL work: a `pow(sin(x), k)` that went NaN at a plane edge (bloom then blackened the frame), and display-referred shader colours being gamma-encoded twice in a post-processing chain.
