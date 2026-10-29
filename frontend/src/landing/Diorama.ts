import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

/*
 * "Sawah di dalam air": a procedural miniature of a Lampung rice landscape inside a block of water.
 *
 * Pipeline per frame:
 *   1. opaque scene  -> HalfFloat target with a depth texture (transparent clear, so the page shows through)
 *   2. copy + water  -> second target; the water shader does a manual depth test and computes colour from the
 *                       real thickness of water along each view ray (Beer-Lambert), refraction, Fresnel sky,
 *                       sun glints, shore foam and click ripples
 *   3. final pass    -> tone mapping, sRGB, tilt-shift and vignette onto a transparent canvas
 *
 * Everything is generated here: no models, no image textures.
 */

/**
 * A camera framing for one chapter of the landing story. `free` hands the camera back to the visitor
 * (drag to orbit); otherwise the camera glides to the given orbit. `sx`/`sy` shift the rendered frame as a
 * fraction of the canvas, so the block can sit beside or above the chapter text.
 */
export type View = { free?: boolean; theta?: number; el?: number; dist?: number; ty?: number; sx: number; sy: number };

export type WaterMode = "kering" | "normal" | "banjir";
export type DioramaHandle = {
  setPointer: (x: number, y: number) => void;
  setScroll: (p: number) => void;
  setView: (v: View) => void;
  setWater: (m: WaterMode) => void;
  setStage: (s: number) => void;
  setHour: (h: number) => void;
  resetView: () => void;
  setActive: (on: boolean) => void;
  dispose: () => void;
};
export type DioramaOptions = {
  mobile: boolean;
  reducedMotion: boolean;
  onProgress?: (done: number, total: number, label: string) => void;
  onStats?: (fps: number) => void;
};

const HALF = 5;
const BOTTOM = -1.1;
const LEVEL: Record<WaterMode, number> = { kering: -0.62, normal: 0.0, banjir: 0.3 };
const KIND = { hill: 0, terrace: 1, plot: 2, bund: 3, sand: 4, village: 5, rock: 6 } as const;

// ---------- small helpers ----------

function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}
function hash2(x: number, y: number) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function vnoise(x: number, y: number) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi), b = hash2(xi + 1, yi), c = hash2(xi, yi + 1), d = hash2(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x: number, y: number) {
  return vnoise(x, y) * 0.55 + vnoise(x * 2.03, y * 2.03) * 0.28 + vnoise(x * 4.1, y * 4.1) * 0.17;
}
const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

// ---------- landscape ----------

const HILL = { x: -0.8, z: -2.6, r: 3.7, h: 2.45 };
const POND = { x: -3.15, z: 3.05, r: 1.25 };
const riverX = (z: number) => 1.75 + Math.sin(z * 0.55 + 0.4) * 0.6;
const PLOT = { w: 0.86, d: 0.64, bund: 0.035 };

function hillDome(x: number, z: number) {
  const d = Math.hypot(x - HILL.x, (z - HILL.z) * 1.08);
  const t = Math.max(0, 1 - (d / HILL.r) ** 2);
  return HILL.h * t ** 1.35 + (fbm(x * 0.9, z * 0.9) - 0.5) * 0.35 * t;
}

type Sample = { h: number; kind: number; flat: number };

function sampleLand(x: number, z: number): Sample {
  // Paddy plain: plots separated by raised bunds (pematang).
  const gx = (x + 7.3) / PLOT.w, gz = (z + 9.1) / PLOT.d;
  const fx = gx - Math.floor(gx), fz = gz - Math.floor(gz);
  const edge = Math.min(fx * PLOT.w, (1 - fx) * PLOT.w, fz * PLOT.d, (1 - fz) * PLOT.d);
  let h: number;
  let kind: number;
  if (edge < PLOT.bund) {
    h = 0.035;
    kind = KIND.bund;
  } else {
    h = -0.045 + (hash2(Math.floor(gx), Math.floor(gz)) - 0.5) * 0.01;
    kind = KIND.plot;
  }
  let flat = 1;

  // The hill, cut into terraces on the side that faces the plain.
  const dome = hillDome(x, z);
  if (dome > 0.02) {
    const faceViewer = smooth(-0.6, 0.6, (z - HILL.z) / HILL.r + 0.25 + (x - HILL.x) * 0.05);
    const step = 0.15;
    const q = dome / step;
    const fq = q - Math.floor(q);
    const terraced = Math.floor(q) * step + step * smooth(0.82, 1.0, fq);
    const inBand = smooth(0.12, 0.25, dome) * (1 - smooth(1.35, 1.6, dome)) * faceViewer;
    const hh = dome + (terraced - dome) * inBand + 0.02;
    if (hh > h) {
      h = hh;
      if (inBand > 0.5 && fq < 0.8) kind = KIND.terrace;
      else kind = dome > 1.2 || inBand < 0.5 ? KIND.hill : KIND.bund;
      flat = inBand > 0.5 && fq < 0.8 ? 1 : 0;
    }
  }

  // Village terrace beyond the river.
  const vx = smooth(2.75, 3.0, x) * (1 - smooth(4.55, 4.7, x));
  const vz = smooth(-2.2, -1.9, z) * (1 - smooth(1.3, 1.6, z));
  const village = vx * vz;
  if (village > 0.01) {
    const vh = 0.13 + (fbm(x * 3, z * 3) - 0.5) * 0.02;
    h = h + (vh - h) * village;
    if (village > 0.5) kind = KIND.village;
  }

  // River from the hill foot to the front edge, with sandy banks.
  const rd = Math.abs(x - riverX(z));
  // The river springs at the foot of the hill, so it never cuts through the terraces.
  const riverOn = smooth(-1.25, -0.7, z) * (1 - smooth(0.25, 0.6, hillDome(x, z)));
  if (rd < 0.5 && riverOn > 0) {
    const bed = -0.58 * (1 - (Math.min(rd, 0.3) / 0.3) ** 2);
    const bank = 1 - smooth(0.3, 0.5, rd);
    const target = rd < 0.3 ? bed : h - 0.06 * bank;
    h = h + (target - h) * riverOn;
    if (rd < 0.42 && riverOn > 0.5) kind = KIND.sand;
    flat = 0;
  }

  // Embung (reservoir) in the front-left corner.
  const pd = Math.hypot(x - POND.x, z - POND.z);
  if (pd < POND.r + 0.35) {
    const t = 1 - smooth(POND.r * 0.35, POND.r, pd);
    h = Math.min(h, -0.08 - 0.75 * t);
    if (pd < POND.r + 0.15) kind = pd > POND.r * 0.85 ? KIND.rock : KIND.sand;
    flat = 0;
  }

  // Falling away to a shelf at the block edge, so water wraps the land.
  const e = HALF - Math.max(Math.abs(x), Math.abs(z));
  const shelf = 1 - smooth(0.25, 1.05, e);
  if (shelf > 0) {
    h = h + (-0.95 + fbm(x * 2, z * 2) * 0.12 - h) * shelf;
    if (shelf > 0.4) kind = h < -0.55 ? KIND.rock : KIND.sand;
    flat = 0;
  }
  return { h, kind, flat };
}

/** Pull grid points in the four corners onto a quarter circle, so the land matches the block's rounded corners. */
function roundCorner(x: number, z: number, half: number, rad: number): [number, number] {
  if (Math.abs(x) <= half - rad || Math.abs(z) <= half - rad) return [x, z];
  const cx = Math.sign(x) * (half - rad), cz = Math.sign(z) * (half - rad);
  const dx = x - cx, dz = z - cz;
  const d = Math.hypot(dx, dz);
  if (d <= rad) return [x, z];
  return [cx + (dx / d) * rad, cz + (dz / d) * rad];
}

const PALETTE: Record<number, THREE.Color> = {
  [KIND.hill]: new THREE.Color("#4d6b33"),
  [KIND.terrace]: new THREE.Color("#6f8a3f"),
  [KIND.plot]: new THREE.Color("#6a5a3e"),
  [KIND.bund]: new THREE.Color("#7e9a49"),
  [KIND.sand]: new THREE.Color("#b8a27a"),
  [KIND.village]: new THREE.Color("#a68c63"),
  [KIND.rock]: new THREE.Color("#7f776c"),
};

function buildTerrain(n: number) {
  const pos: number[] = [], col: number[] = [], kinds: number[] = [], aos: number[] = [];
  const hs: number[] = [];
  const tmp = new THREE.Color();
  for (let j = 0; j <= n; j++)
    for (let i = 0; i <= n; i++) {
      let x = -HALF + (i / n) * 2 * HALF;
      let z = -HALF + (j / n) * 2 * HALF;
      [x, z] = roundCorner(x, z, HALF - 0.02, 0.6);
      const s = sampleLand(x, z);
      pos.push(x, s.h, z);
      hs.push(s.h);
      kinds.push(s.kind);
      tmp.copy(PALETTE[s.kind]);
      const v = 0.88 + fbm(x * 4.3, z * 4.3) * 0.24;
      tmp.multiplyScalar(v);
      col.push(tmp.r, tmp.g, tmp.b);
    }
  // Horizon ambient occlusion: how much higher land rises around each vertex.
  const at = (i: number, j: number) => hs[Math.min(n, Math.max(0, j)) * (n + 1) + Math.min(n, Math.max(0, i))];
  const cell = (2 * HALF) / n;
  for (let j = 0; j <= n; j++)
    for (let i = 0; i <= n; i++) {
      const h0 = at(i, j);
      let occ = 0;
      for (let k = 0; k < 8; k++) {
        const a = (k / 8) * Math.PI * 2;
        let best = 0;
        for (const r of [2, 5, 10]) {
          const dh = at(i + Math.round(Math.cos(a) * r), j + Math.round(Math.sin(a) * r)) - h0;
          best = Math.max(best, dh / (r * cell));
        }
        occ += Math.atan(best) / (Math.PI / 2);
      }
      aos.push(1 - Math.min(0.65, (occ / 8) * 1.1));
    }
  const idx: number[] = [];
  for (let j = 0; j < n; j++)
    for (let i = 0; i < n; i++) {
      const a = j * (n + 1) + i, b = a + 1, c = a + n + 1, d = c + 1;
      idx.push(a, c, b, b, c, d);
    }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  g.setAttribute("aKind", new THREE.Float32BufferAttribute(kinds, 1));
  g.setAttribute("aAo", new THREE.Float32BufferAttribute(aos, 1));
  g.setIndex(idx);
  g.computeVertexNormals();

  // Skirt: the cut face of the land, visible through the glass-like water walls.
  const skirtPos: number[] = [], skirtCol: number[] = [];
  const ring: [number, number][] = [];
  for (let i = 0; i < n; i++) ring.push([i, 0]);
  for (let j = 0; j < n; j++) ring.push([n, j]);
  for (let i = n; i > 0; i--) ring.push([i, n]);
  for (let j = n; j > 0; j--) ring.push([0, j]);
  const soilTop = new THREE.Color("#6d5536"), soilDeep = new THREE.Color("#3e3020");
  for (let k = 0; k < ring.length; k++) {
    const [i0, j0] = ring[k], [i1, j1] = ring[(k + 1) % ring.length];
    const p0 = j0 * (n + 1) + i0, p1 = j1 * (n + 1) + i1;
    const x0 = pos[p0 * 3], y0 = pos[p0 * 3 + 1], z0 = pos[p0 * 3 + 2];
    const x1 = pos[p1 * 3], y1 = pos[p1 * 3 + 1], z1 = pos[p1 * 3 + 2];
    skirtPos.push(x0, y0, z0, x0, BOTTOM, z0, x1, y1, z1, x1, y1, z1, x0, BOTTOM, z0, x1, BOTTOM, z1);
    for (const y of [y0, BOTTOM, y1, y1, BOTTOM, BOTTOM]) {
      const t = (y - BOTTOM) / 3;
      const c = soilDeep.clone().lerp(soilTop, Math.min(1, t * 2.2));
      skirtCol.push(c.r, c.g, c.b);
    }
  }
  const skirt = new THREE.BufferGeometry();
  skirt.setAttribute("position", new THREE.Float32BufferAttribute(skirtPos, 3));
  skirt.setAttribute("color", new THREE.Float32BufferAttribute(skirtCol, 3));
  skirt.computeVertexNormals();
  return { terrain: g, skirt };
}

// ---------- shaders shared by the land ----------

const CAUSTIC_GLSL = /* glsl */ `
  float cHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float caustic(vec2 p, float t) {
    // Two drifting cell layers; bright where cell edges meet, like light focused by a wavy surface.
    float c = 0.0;
    for (int k = 0; k < 2; k++) {
      vec2 q = p * (k == 0 ? 3.1 : 4.7) + vec2(t * 0.35, -t * 0.27) * (k == 0 ? 1.0 : -0.8);
      vec2 i = floor(q), f = fract(q);
      float d1 = 8.0, d2 = 8.0;
      for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
        vec2 g = vec2(float(x), float(y));
        vec2 o = vec2(cHash(i + g), cHash(i + g + 17.3));
        o = 0.5 + 0.45 * sin(t * 0.9 + 6.2831 * o);
        float d = length(g + o - f);
        if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
      }
      c += pow(1.0 - smoothstep(0.0, 0.18, d2 - d1), 3.0);
    }
    return c * 0.5;
  }
  float crackNoise(vec2 p) {
    vec2 i = floor(p * 9.0), f = fract(p * 9.0);
    float d1 = 8.0, d2 = 8.0;
    for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
      vec2 g = vec2(float(x), float(y));
      vec2 o = vec2(cHash(i + g), cHash(i + g + 5.1));
      float d = length(g + o - f);
      if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
    }
    return 1.0 - smoothstep(0.0, 0.07, d2 - d1);
  }
`;

type LandUniforms = {
  uLevel: { value: number };
  uTime: { value: number };
  uDry: { value: number };
  uWet: { value: number };
  uFlood: { value: number };
};

function landMaterial(u: LandUniforms) {
  const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0, envMapIntensity: 0.6 });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, u);
    sh.vertexShader = sh.vertexShader
      .replace(
        "#include <common>",
        "#include <common>\nattribute float aKind;\nattribute float aAo;\nvarying float vKind;\nvarying float vAo;\nvarying vec3 vWPos;",
      )
      .replace(
        "#include <worldpos_vertex>",
        "#include <worldpos_vertex>\nvKind = aKind; vAo = aAo; vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;",
      );
    sh.fragmentShader = sh.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform float uLevel, uTime, uDry, uWet, uFlood;\nvarying float vKind;\nvarying float vAo;\nvarying vec3 vWPos;\n" +
          CAUSTIC_GLSL,
      )
      .replace(
        "#include <color_fragment>",
        /* glsl */ `#include <color_fragment>
        float isPlot = step(1.5, vKind) * step(vKind, 2.5);
        float isTerrace = step(0.5, vKind) * step(vKind, 1.5);
        float paddy = max(isPlot, isTerrace);
        // Drought: paddy soil dries pale and cracks.
        vec3 dryCol = vec3(0.66, 0.56, 0.40) * (1.0 - crackNoise(vWPos.xz) * 0.55);
        diffuseColor.rgb = mix(diffuseColor.rgb, dryCol, uDry * paddy);
        // Every petak is a little different: soil tone, puddling, when it was last worked.
        float plotId = cHash(floor(vec2((vWPos.x + 7.3) / 0.86, (vWPos.z + 9.1) / 0.64)));
        diffuseColor.rgb *= mix(1.0, 0.82 + 0.34 * plotId, isPlot);
        // Irrigated paddies hold a few centimetres of standing water: dark, glossy, tinted by the sky.
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.22, 0.29, 0.27) * (0.88 + 0.24 * plotId), uWet * isPlot * 0.72);
        // Terraces hold their own shallow water when irrigated.
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.27, 0.36, 0.33), uWet * isTerrace * 0.6);
        // Floods leave a muddy film on everything they reach.
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.42, 0.36, 0.26), uFlood * step(vWPos.y, uLevel + 0.02) * 0.5);
        float depth = uLevel - vWPos.y;
        // Damp, darker band of soil just above the waterline.
        float wetBand = smoothstep(-0.06, 0.0, depth) * step(depth, 0.0);
        diffuseColor.rgb *= 1.0 - 0.28 * wetBand;
        if (depth > 0.0) {
          diffuseColor.rgb *= mix(1.0, 0.72, smoothstep(0.0, 0.4, depth));
          diffuseColor.rgb += vec3(0.9, 0.95, 0.85) * caustic(vWPos.xz, uTime) * 0.32 * exp(-depth * 2.2) * (1.0 - uFlood * 0.8);
        }
        diffuseColor.rgb *= vAo;`,
      )
      .replace(
        "#include <roughnessmap_fragment>",
        `#include <roughnessmap_fragment>
        roughnessFactor = mix(roughnessFactor, 0.24, uWet * step(0.5, vKind) * step(vKind, 2.5));`,
      );
  };
  m.customProgramCacheKey = () => "jagapadi-land";
  return m;
}

// ---------- geometry builder for architecture and palms ----------

class Builder {
  parts: THREE.BufferGeometry[] = [];
  add(geo: THREE.BufferGeometry, color: string | THREE.Color, m: THREE.Matrix4) {
    const g = (geo.index ? geo.toNonIndexed() : geo.clone()).applyMatrix4(m);
    g.deleteAttribute("uv");
    if (!g.attributes.normal) g.computeVertexNormals();
    const c = new THREE.Color(color);
    const arr = new Float32Array(g.attributes.position.count * 3);
    for (let i = 0; i < arr.length; i += 3) arr.set([c.r, c.g, c.b], i);
    g.setAttribute("color", new THREE.BufferAttribute(arr, 3));
    this.parts.push(g);
  }
  box(w: number, h: number, d: number, color: string, at: THREE.Vector3, rotY = 0) {
    this.add(new THREE.BoxGeometry(w, h, d), color, new THREE.Matrix4().compose(at, new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rotY), new THREE.Vector3(1, 1, 1)));
  }
  cyl(r: number, h: number, color: string, at: THREE.Vector3, seg = 6) {
    this.add(new THREE.CylinderGeometry(r, r, h, seg), color, new THREE.Matrix4().makeTranslation(at.x, at.y, at.z));
  }
  place(geo: THREE.BufferGeometry, m: THREE.Matrix4) {
    this.parts.push(geo.clone().applyMatrix4(m));
  }
  merged() {
    return this.parts.length ? mergeGeometries(this.parts, false) : new THREE.BufferGeometry();
  }
}

/** Hip roof: trapezoid front and back, triangular ends. */
function hipRoof(w: number, d: number, h: number) {
  const ridge = Math.max(0, w - d) / 2;
  const v = [
    [-w / 2, 0, -d / 2], [w / 2, 0, -d / 2], [w / 2, 0, d / 2], [-w / 2, 0, d / 2],
    [-ridge, h, 0], [ridge, h, 0],
  ];
  const f = [
    [0, 4, 5], [0, 5, 1],
    [2, 5, 4], [2, 4, 3],
    [1, 5, 2], [3, 4, 0],
  ];
  const pos: number[] = [];
  for (const t of f) for (const k of t) pos.push(...v[k]);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.computeVertexNormals();
  return g;
}

function buildArchitecture(r: () => number) {
  const b = new Builder();
  const glow = new Builder();

  // Rumah panggung: wooden houses on stilts with hip roofs, around a musholla.
  const houses: [number, number, number, string][] = [
    [3.25, -1.55, 0.1, "#8a5a36"], [4.1, -1.35, -0.2, "#d8c7a3"], [3.3, -0.55, 0.05, "#c9b08a"],
    [4.15, -0.3, 0.15, "#8a5a36"], [3.35, 0.55, -0.1, "#d8c7a3"], [4.2, 0.85, 0.2, "#7a4e30"],
  ];
  for (const [x, z, rot, wall] of houses) {
    const base = sampleLand(x, z).h;
    const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rot);
    const m = (lx: number, ly: number, lz: number) => new THREE.Vector3(lx, ly, lz).applyQuaternion(q).add(new THREE.Vector3(x, base, z));
    for (const [sx, sz] of [[-0.2, -0.13], [0.2, -0.13], [-0.2, 0.13], [0.2, 0.13], [0, -0.13], [0, 0.13]])
      b.cyl(0.018, 0.16, "#5a3f2a", m(sx, 0.08, sz));
    b.box(0.5, 0.025, 0.34, "#6b4a30", m(0, 0.165, 0), rot);
    b.box(0.44, 0.2, 0.28, wall, m(0, 0.28, 0), rot);
    const roofM = new THREE.Matrix4().compose(m(0, 0.375, 0), q, new THREE.Vector3(1, 1, 1));
    b.add(hipRoof(0.6, 0.42, 0.2), "#8c3a26", roofM);
    b.box(0.32, 0.03, 0.3, "#6b4a30", m(0, 0.17, 0.27), rot); // front porch
    for (const wx of [-0.12, 0.12]) glow.box(0.07, 0.07, 0.01, "#ffd08a", m(wx, 0.29, 0.142), rot);
  }
  // Musholla: white walls, green dome.
  {
    const x = 3.75, z = 1.15, base = sampleLand(x, z).h;
    b.box(0.42, 0.24, 0.42, "#efe9dc", new THREE.Vector3(x, base + 0.12, z));
    b.box(0.46, 0.03, 0.46, "#c9c1ae", new THREE.Vector3(x, base + 0.255, z));
    b.add(new THREE.SphereGeometry(0.15, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), "#3f7d5a", new THREE.Matrix4().makeTranslation(x, base + 0.27, z));
    b.cyl(0.008, 0.08, "#c9a04a", new THREE.Vector3(x, base + 0.46, z));
    glow.box(0.09, 0.11, 0.01, "#ffd08a", new THREE.Vector3(x, base + 0.12, z + 0.212));
  }
  // Dangau: open field huts with thatched roofs.
  for (const [x, z] of [[-1.3, 1.6], [0.7, 3.1], [-2.4, 0.4]] as [number, number][]) {
    const base = sampleLand(x, z).h;
    for (const [sx, sz] of [[-0.09, -0.09], [0.09, -0.09], [-0.09, 0.09], [0.09, 0.09]])
      b.cyl(0.012, 0.2, "#6a4a2e", new THREE.Vector3(x + sx, base + 0.1, z + sz));
    b.box(0.22, 0.02, 0.22, "#7a5a38", new THREE.Vector3(x, base + 0.1, z));
    b.add(hipRoof(0.32, 0.3, 0.16), "#c9a35c", new THREE.Matrix4().makeTranslation(x, base + 0.2, z));
  }
  // Pintu air (sluice gate) where the canal leaves the river, and a footbridge to the village.
  {
    const z = -1.2, x = riverX(z);
    for (const s of [-0.34, 0.34]) b.box(0.08, 0.5, 0.12, "#b9b4aa", new THREE.Vector3(x + s, -0.12, z));
    b.box(0.76, 0.06, 0.14, "#b9b4aa", new THREE.Vector3(x, 0.15, z));
    b.box(0.56, 0.36, 0.03, "#3d6e8f", new THREE.Vector3(x, -0.12, z));
    b.cyl(0.03, 0.12, "#5a6a72", new THREE.Vector3(x, 0.24, z));
  }
  {
    const z = 0.25, x = riverX(z);
    b.box(0.95, 0.03, 0.16, "#7a5a38", new THREE.Vector3(x + 0.05, 0.1, z), 0.1);
    for (const s of [-0.075, 0.075]) b.box(0.95, 0.06, 0.012, "#5a3f2a", new THREE.Vector3(x + 0.05, 0.15, z + s), 0.1);
    for (const s of [-0.38, 0.38]) b.cyl(0.02, 0.6, "#5a3f2a", new THREE.Vector3(x + s, -0.2, z));
  }
  // Coconut palms along the river and the village.
  const palmSpots: [number, number][] = [
    [2.65, -1.9], [2.7, 1.9], [4.5, 1.6], [4.55, -2.0], [2.5, 3.3], [1.0, -1.6], [-1.75, 4.15], [-4.1, 1.9], [2.9, -0.95], [4.6, -0.8],
  ];
  for (const [x, z] of palmSpots) {
    const base = sampleLand(x, z).h;
    const lean = new THREE.Vector3(r() - 0.5, 0, r() - 0.5).normalize().multiplyScalar(0.12);
    const h = 0.7 + r() * 0.25;
    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(x, base, z),
      new THREE.Vector3(x + lean.x * 0.3, base + h * 0.6, z + lean.z * 0.3),
      new THREE.Vector3(x + lean.x, base + h, z + lean.z),
    );
    b.add(new THREE.TubeGeometry(curve, 8, 0.018, 5, false), "#7d6a52", new THREE.Matrix4());
    const top = curve.getPoint(1);
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2 + r() * 0.3;
      const frond = new THREE.PlaneGeometry(0.42, 0.07, 6, 1);
      const p = frond.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < p.count; i++) {
        const fx = p.getX(i) + 0.21;
        p.setXYZ(i, fx, -fx * fx * 0.9, p.getY(i) * (1 - fx / 0.5));
      }
      const m = new THREE.Matrix4().compose(top, new THREE.Quaternion().setFromEuler(new THREE.Euler(0, a, 0.15)), new THREE.Vector3(1, 1, 1));
      b.add(frond, k % 2 ? "#4f7a2f" : "#5f8a35", m);
    }
  }
  return { solid: b.merged(), glow: glow.merged() };
}

// ---------- life in the fields ----------

/** Points inside paddy plots, away from the river, the reservoir and each other. */
function plotSpots(r: () => number, n: number, gap: number, taken: [number, number][]) {
  const out: [number, number][] = [];
  let guard = 0;
  while (out.length < n && guard++ < n * 400) {
    const x = (r() * 2 - 1) * (HALF - 1.0), z = (r() * 2 - 1) * (HALF - 1.0);
    const s = sampleLand(x, z);
    if (s.kind !== KIND.plot || s.h >= 0) continue;
    if (Math.abs(x - riverX(z)) < 0.75 || Math.hypot(x - POND.x, z - POND.z) < POND.r + 0.5 || hillDome(x, z) > 0.01) continue;
    if ([...taken, ...out].some(([tx, tz]) => Math.hypot(tx - x, tz - z) < gap)) continue;
    out.push([x, z]);
  }
  taken.push(...out);
  return out;
}

const at = (x: number, y: number, z: number, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1) =>
  new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz, "YXZ")), new THREE.Vector3(sx, sy, sz));

/** A small figure built facing +z at the origin, then placed: miniature scale, so it reads from the camera. */
function figure(build: (b: Builder) => void) {
  const b = new Builder();
  build(b);
  return b.merged();
}

const SHIRTS = ["#3d6e8f", "#b5523b", "#e6dcc3", "#5b7d4a", "#7a4b6b"];

function farmer(shirt: string, bend: number) {
  return figure((b) => {
    const sphere = new THREE.SphereGeometry(1, 10, 8);
    for (const sx of [-0.016, 0.016]) b.add(new THREE.CylinderGeometry(0.008, 0.009, 0.07, 6), "#2f2a26", at(sx, 0.035, 0));
    const lean = new THREE.Euler(bend, 0, 0);
    b.add(new THREE.CylinderGeometry(0.019, 0.023, 0.065, 8).translate(0, 0.0325, 0), shirt, at(0, 0.07, 0, bend));
    const shoulder = new THREE.Vector3(0, 0.062, 0).applyEuler(lean).add(new THREE.Vector3(0, 0.07, 0));
    for (const sx of [-0.022, 0.022])
      b.add(new THREE.CylinderGeometry(0.006, 0.006, 0.06, 5).translate(0, -0.03, 0), shirt, at(shoulder.x + sx, shoulder.y, shoulder.z, bend * 0.3));
    const head = new THREE.Vector3(0, 0.083, 0).applyEuler(lean).add(new THREE.Vector3(0, 0.07, 0));
    b.add(sphere, "#9a6a46", at(head.x, head.y, head.z, 0, 0, 0, 0.014, 0.015, 0.014));
    b.add(new THREE.ConeGeometry(0.05, 0.026, 14), "#d9c08a", at(head.x, head.y + 0.014, head.z, bend * 0.5));
  });
}

function egret() {
  return figure((b) => {
    const sphere = new THREE.SphereGeometry(1, 10, 8);
    for (const sx of [-0.006, 0.006]) b.add(new THREE.CylinderGeometry(0.0025, 0.0025, 0.045, 4), "#3a3530", at(sx, 0.022, 0));
    b.add(sphere, "#f6f4ee", at(0, 0.055, 0, 0, 0, 0, 0.014, 0.012, 0.026));
    b.add(new THREE.CylinderGeometry(0.0035, 0.004, 0.035, 5).translate(0, 0.0175, 0), "#f6f4ee", at(0, 0.062, 0.018, 0.35));
    b.add(sphere, "#f6f4ee", at(0, 0.094, 0.03, 0, 0, 0, 0.0065, 0.0065, 0.0065));
    b.add(new THREE.ConeGeometry(0.0025, 0.022, 4), "#e0b23a", at(0, 0.093, 0.045, Math.PI / 2));
  });
}

function buffalo() {
  return figure((b) => {
    const sphere = new THREE.SphereGeometry(1, 12, 10);
    const hide = "#4b4643";
    for (const [lx, lz] of [[-0.035, -0.06], [0.035, -0.06], [-0.035, 0.06], [0.035, 0.06]]) b.add(new THREE.CylinderGeometry(0.011, 0.01, 0.06, 6), hide, at(lx, 0.03, lz));
    b.add(sphere, hide, at(0, 0.08, 0, 0, 0, 0, 0.05, 0.045, 0.1));
    b.add(sphere, "#3f3a37", at(0, 0.085, 0.115, 0.4, 0, 0, 0.026, 0.026, 0.04));
    for (const sx of [-1, 1]) b.add(new THREE.TorusGeometry(0.03, 0.005, 5, 10, Math.PI * 0.8), "#cdbf9f", at(sx * 0.018, 0.105, 0.105, 0, sx > 0 ? 0 : Math.PI, 0, 1, 0.7, 1));
  });
}

function scarecrow(shirt: string) {
  return figure((b) => {
    b.add(new THREE.CylinderGeometry(0.005, 0.006, 0.2, 5), "#6a4a2e", at(0, 0.1, 0));
    b.add(new THREE.BoxGeometry(0.12, 0.008, 0.008), "#6a4a2e", at(0, 0.155, 0));
    b.add(new THREE.BoxGeometry(0.07, 0.06, 0.03), shirt, at(0, 0.13, 0, 0, 0, 0.08));
    b.add(new THREE.SphereGeometry(1, 10, 8), "#d8c7a3", at(0, 0.19, 0, 0, 0, 0, 0.016, 0.018, 0.016));
    b.add(new THREE.ConeGeometry(0.045, 0.024, 12), "#c9a35c", at(0, 0.212, 0, 0.15));
  });
}

function buildLife(r: () => number) {
  const b = new Builder();
  const taken: [number, number][] = [];
  const put = (geo: THREE.BufferGeometry, x: number, z: number, scale: number) => {
    const y = sampleLand(x, z).h;
    b.place(geo, at(x, y, z, 0, r() * Math.PI * 2, 0, scale, scale, scale));
  };
  // Petani in caping hats, bent over the rice: planting or weeding.
  for (const [x, z] of plotSpots(r, 8, 0.9, taken)) put(farmer(SHIRTS[Math.floor(r() * SHIRTS.length)], 0.65 + r() * 0.4), x, z, 1.9);
  // A pair standing upright, talking at the edge of a plot.
  for (const [x, z] of plotSpots(r, 1, 1.2, taken)) {
    put(farmer(SHIRTS[0], 0.05), x, z, 1.9);
    put(farmer(SHIRTS[1], 0.1), x + 0.12, z + 0.05, 1.9);
  }
  // Kuntul (egrets) wading between the rows.
  for (const [x, z] of plotSpots(r, 16, 0.35, taken)) put(egret(), x, z, 2.1);
  // Kerbau (water buffalo): out of the rice, where they can be seen. Two graze the grass at the foot of the
  // hill on the side facing the camera, one wallows in the shallows of the embung.
  const grazing: [number, number][] = [];
  for (let guard = 0; grazing.length < 2 && guard < 4000; guard++) {
    const x = HILL.x + (r() * 2 - 1) * HILL.r, z = HILL.z + r() * HILL.r;
    const s = sampleLand(x, z), dome = hillDome(x, z);
    if (dome < 0.04 || dome > 0.22 || s.kind === KIND.plot || s.kind === KIND.terrace || s.h < 0.02) continue;
    if (Math.abs(x - riverX(z)) < 0.7 || x + z < -1.2) continue;
    if (grazing.some(([gx, gz]) => Math.hypot(gx - x, gz - z) < 0.6)) continue;
    grazing.push([x, z]);
  }
  for (const [x, z] of grazing) put(buffalo(), x, z, 2.4);
  {
    const a = -0.6, x = POND.x + Math.cos(a) * POND.r * 0.86, z = POND.z + Math.sin(a) * POND.r * 0.86;
    b.place(buffalo(), at(x, sampleLand(x, z).h - 0.06, z, 0, 2.2, 0, 2.4, 2.4, 2.4));
  }
  // Orang-orangan sawah (scarecrows).
  for (const [x, z] of plotSpots(r, 3, 1.2, taken)) put(scarecrow(SHIRTS[Math.floor(r() * SHIRTS.length)]), x, z, 1.5);

  // Pisang (banana plants) around the village and the field huts.
  const bananas: [number, number][] = [[2.95, -1.95], [4.45, 0.3], [3.0, 1.35], [4.5, -1.75], [-1.05, 1.85], [0.95, 3.35], [-2.65, 0.6], [3.9, 1.65]];
  for (const [x, z] of bananas) {
    const y = sampleLand(x, z).h;
    const h = 0.26 + r() * 0.08;
    b.add(new THREE.CylinderGeometry(0.016, 0.022, h, 6), "#7c8a4a", new THREE.Matrix4().makeTranslation(x, y + h / 2, z));
    for (let k = 0; k < 6; k++) {
      const leaf = new THREE.PlaneGeometry(0.26, 0.08, 6, 1);
      const pa = leaf.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < pa.count; i++) {
        const lx = pa.getX(i) + 0.13;
        pa.setXYZ(i, lx, 0.05 * Math.sin((lx / 0.26) * Math.PI) - lx * lx * 1.2, pa.getY(i) * Math.sin(Math.min(1, lx / 0.26 + 0.15) * Math.PI));
      }
      b.add(leaf, k % 2 ? "#6f9a3a" : "#88ad4a", at(x, y + h, z, 0, (k / 6) * Math.PI * 2 + r() * 0.4, 0.25 + r() * 0.25));
    }
  }
  return b.merged();
}

/** A wooden perahu with a fisherman, built at the origin so it can ride the water level. */
function buildBoat() {
  const b = new Builder();
  const hull = new THREE.CylinderGeometry(0.06, 0.06, 0.42, 10, 1, true, Math.PI / 2, Math.PI);
  hull.rotateZ(Math.PI / 2);
  hull.scale(1, 0.55, 1);
  b.add(hull, "#7a4e30", new THREE.Matrix4());
  for (const s of [-1, 1]) b.add(new THREE.ConeGeometry(0.06, 0.09, 10, 1, false, Math.PI / 2, Math.PI), "#6b4429", at(s * 0.255, 0, 0, 0, 0, -s * Math.PI / 2, 1, 1, 0.55));
  b.add(new THREE.BoxGeometry(0.03, 0.01, 0.11), "#5a3a24", at(0.06, -0.005, 0));
  b.add(new THREE.CylinderGeometry(0.016, 0.02, 0.05, 8), "#b5523b", at(0.06, 0.02, 0));
  b.add(new THREE.SphereGeometry(0.012, 8, 6), "#9a6a46", at(0.06, 0.055, 0));
  b.add(new THREE.ConeGeometry(0.04, 0.022, 14), "#d9c08a", at(0.06, 0.068, 0));
  b.add(new THREE.CylinderGeometry(0.003, 0.003, 0.32, 4), "#6a4a2e", at(0.0, 0.05, 0.04, 0, 0, 1.1));
  return b.merged();
}

// ---------- vegetation ----------

function blobGeometry(detail: number) {
  const g = new THREE.IcosahedronGeometry(1, detail);
  const p = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < p.count; i++) {
    const v = new THREE.Vector3().fromBufferAttribute(p, i);
    const n = fbm(v.x * 2.1 + 3, v.z * 2.1 + v.y * 1.7);
    v.multiplyScalar(0.82 + n * 0.36);
    v.y *= 0.82;
    p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}

function buildForest(r: () => number, count: number) {
  const pts: { p: THREE.Vector3; s: number }[] = [];
  let guard = 0;
  while (pts.length < count && guard++ < count * 30) {
    const x = (r() * 2 - 1) * (HALF - 0.5), z = (r() * 2 - 1) * (HALF - 0.5);
    const s = sampleLand(x, z);
    const dome = hillDome(x, z);
    const rd = Math.abs(x - riverX(z));
    let ok = false;
    if (s.kind === KIND.hill && dome > 0.3) ok = r() < 0.95;
    else if (rd > 0.42 && rd < 0.75 && z > -2) ok = r() < 0.18;
    else if (Math.hypot(x - POND.x, z - POND.z) < POND.r + 0.6 && s.h > -0.05) ok = r() < 0.4;
    if (!ok || s.h < -0.05) continue;
    const tree = 2 + Math.floor(r() * 3);
    const base = 0.11 + r() * 0.08 + dome * 0.015;
    for (let k = 0; k < tree && pts.length < count; k++) {
      const off = new THREE.Vector3((r() - 0.5) * base * 1.4, base * (0.8 + k * 0.45), (r() - 0.5) * base * 1.4);
      pts.push({ p: new THREE.Vector3(x, s.h, z).add(off), s: base * (1 - k * 0.15) * (0.85 + r() * 0.3) });
    }
  }
  return pts;
}

function treeMaterial(uDry: { value: number }) {
  const m = new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: 0 });
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uDry = uDry;
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying float vUp;")
      .replace("#include <beginnormal_vertex>", "#include <beginnormal_vertex>\nvUp = objectNormal.y;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying float vUp;\nuniform float uDry;")
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
         diffuseColor.rgb *= 0.72 + 0.45 * smoothstep(-0.4, 0.9, vUp);
         diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(1.15, 0.95, 0.6), uDry * 0.45);`,
      );
  };
  m.customProgramCacheKey = () => "jagapadi-tree";
  return m;
}

function riceMaterial(u: { uStage: { value: number }; uDry: { value: number }; uTime: { value: number } }) {
  const m = new THREE.MeshStandardMaterial({ roughness: 0.92, metalness: 0, side: THREE.DoubleSide, envMapIntensity: 0.35 });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, u);
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nuniform float uStage, uTime;\nattribute float aRand;\nvarying float vH;\nvarying float vRand;\nvarying float vPlot;")
      .replace(
        "#include <begin_vertex>",
        /* glsl */ `#include <begin_vertex>
        // Height by growth stage: seedlings, tall green, heavy and bent, then stubble after harvest.
        vec4 ip = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        vPlot = fract(sin(dot(floor(vec2((ip.x + 7.3) / 0.86, (ip.z + 9.1) / 0.64)), vec2(127.1, 311.7))) * 43758.5453);
        float hScale = uStage < 1.0 ? mix(0.35, 1.0, uStage) : uStage < 2.0 ? 1.0 : uStage < 3.0 ? mix(1.0, 0.95, uStage - 2.0) : mix(0.95, 0.22, clamp(uStage - 3.0, 0.0, 1.0));
        transformed.y *= hScale * (0.85 + aRand * 0.3) * (0.86 + vPlot * 0.28);
        vH = position.y / 0.12;
        vRand = aRand;
        float bend = (0.05 + 0.04 * sin(uTime * 1.7 + ip.x * 3.1 + ip.z * 2.3)) * (1.0 + clamp(uStage - 1.5, 0.0, 1.0) * 1.6);
        transformed.x += bend * vH * vH * hScale * 0.12;`,
      );
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform float uStage, uDry;\nvarying float vH;\nvarying float vRand;\nvarying float vPlot;")
      .replace(
        "#include <color_fragment>",
        /* glsl */ `#include <color_fragment>
        vec3 young = vec3(0.50, 0.78, 0.28), green = vec3(0.32, 0.56, 0.18), gold = vec3(0.86, 0.70, 0.30), stubble = vec3(0.62, 0.52, 0.34);
        // Neighbouring plots were planted days apart, so they ripen a little out of step.
        float st = clamp(uStage + (vPlot - 0.5) * 0.45, 0.0, 4.0);
        vec3 c = st < 1.0 ? mix(young, green, st) : st < 2.0 ? mix(green, gold, st - 1.0) : st < 3.0 ? gold : mix(gold, stubble, clamp(st - 3.0, 0.0, 1.0));
        c = mix(c, vec3(0.62, 0.55, 0.36), uDry * 0.75);
        c *= (0.5 + 0.45 * vH) * 0.85;
        c *= (0.9 + vRand * 0.2) * (0.9 + vPlot * 0.2);
        diffuseColor.rgb = c;`,
      );
  };
  m.customProgramCacheKey = () => "jagapadi-rice";
  return m;
}

function riceTuft() {
  // Five blades, each bending outward over two segments, splayed around the stem: a clump from any angle.
  const parts: THREE.BufferGeometry[] = [];
  const n = 5;
  for (let k = 0; k < n; k++) {
    const w = 0.012, lean = 0.018 + (k % 2) * 0.012;
    const b0 = [-w, 0], b1 = [w, 0];
    const m0 = [-w * 0.7 + lean * 0.35, 0.068], m1 = [w * 0.7 + lean * 0.35, 0.068];
    const tip = [lean, 0.12 - (k % 2) * 0.012];
    const pos: number[] = [], nor: number[] = [];
    for (const [x, y] of [b0, b1, m1, b0, m1, m0, m0, m1, tip]) {
      pos.push(x, y, 0);
      nor.push(x * 6, 0.45 + y * 2, 1);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    g.normalizeNormals();
    g.rotateY((k / n) * Math.PI * 2);
    parts.push(g);
  }
  return mergeGeometries(parts, false);
}

function buildRicePositions(r: () => number, max: number) {
  const out: THREE.Matrix4[] = [];
  const spacing = 0.064;
  const q = new THREE.Quaternion();
  for (let z = -HALF + 0.3; z < HALF - 0.3; z += spacing * 0.9)
    for (let x = -HALF + 0.3; x < HALF - 0.3; x += spacing) {
      const jx = x + (r() - 0.5) * 0.02, jz = z + (r() - 0.5) * 0.02;
      const s = sampleLand(jx, jz);
      if (!((s.kind === KIND.plot && s.h < 0) || (s.kind === KIND.terrace && s.flat > 0.5))) continue;
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), r() * Math.PI);
      out.push(new THREE.Matrix4().compose(new THREE.Vector3(jx, s.h, jz), q, new THREE.Vector3(1, 1, 1)));
    }
  if (out.length <= max) return out;
  const stride = out.length / max;
  return Array.from({ length: max }, (_, i) => out[Math.floor(i * stride)]);
}

// ---------- water ----------

function waterMaterial(rtScene: THREE.WebGLRenderTarget) {
  return new THREE.ShaderMaterial({
    transparent: false,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      tScene: { value: rtScene.texture },
      tDepth: { value: rtScene.depthTexture },
      uRes: { value: new THREE.Vector2(1, 1) },
      uNear: { value: 0.1 },
      uFar: { value: 100 },
      uTime: { value: 0 },
      uLevel: { value: 0 },
      uBottom: { value: BOTTOM },
      uHalf: { value: HALF },
      uSunDir: { value: new THREE.Vector3(0.4, 0.7, 0.3) },
      uSunCol: { value: new THREE.Color(1, 0.95, 0.85) },
      uSkyTop: { value: new THREE.Color("#9cc7e6") },
      uSkyHorizon: { value: new THREE.Color("#f3e7d6") },
      uScatter: { value: new THREE.Color("#2f8c9c") },
      uAbsorb: { value: new THREE.Vector3(0.75, 0.24, 0.16) },
      uMud: { value: 0 },
      uRipples: { value: Array.from({ length: 6 }, () => new THREE.Vector4(0, 0, -100, 0)) },
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      varying vec3 vNormalW;
      varying float vViewZ;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        vNormalW = normalize(mat3(modelMatrix) * normal);
        vec4 mv = viewMatrix * w;
        vViewZ = mv.z;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */ `
      #include <packing>
      uniform sampler2D tScene, tDepth;
      uniform vec2 uRes;
      uniform float uNear, uFar, uTime, uLevel, uBottom, uHalf, uMud;
      uniform vec3 uSunDir, uSunCol, uSkyTop, uSkyHorizon, uScatter, uAbsorb;
      uniform vec4 uRipples[6];
      varying vec3 vWorld;
      varying vec3 vNormalW;
      varying float vViewZ;

      float wHash(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
      float wNoise(vec2 p) {
        vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(wHash(i), wHash(i + vec2(1, 0)), f.x), mix(wHash(i + vec2(0, 1)), wHash(i + vec2(1, 1)), f.x), f.y);
      }
      float surface(vec2 p) {
        float h = wNoise(p * 3.0 + vec2(uTime * 0.25, uTime * 0.18)) * 0.6 + wNoise(p * 7.0 - vec2(uTime * 0.31, -uTime * 0.22)) * 0.4;
        h *= 0.012;
        for (int i = 0; i < 6; i++) {
          vec4 r = uRipples[i];
          float age = uTime - r.z;
          if (age < 0.0 || age > 4.0) continue;
          float d = length(p - r.xy);
          float front = age * 0.9;
          h += sin((d - front) * 22.0) * exp(-abs(d - front) * 9.0) * exp(-age * 1.1) * 0.02 * r.w;
        }
        return h;
      }
      float viewZAt(vec2 uv) { return perspectiveDepthToViewZ(texture2D(tDepth, uv).x, uNear, uFar); }

      void main() {
        vec2 uv = gl_FragCoord.xy / uRes;
        float sceneZ = viewZAt(uv);
        // Manual depth test: land in front of this water surface wins.
        if (sceneZ > vViewZ + 0.002) discard;

        vec3 ro = cameraPosition;
        vec3 rd = normalize(vWorld - ro);
        float entry = length(vWorld - ro);
        // Distance to the land behind along this ray, from view-space depth ratios.
        float sceneDist = texture2D(tDepth, uv).x >= 0.9999 ? 1e4 : entry * (sceneZ / vViewZ);
        // Exit from the water box (slab test), so walls seen edge-on still have finite thickness.
        vec3 bmin = vec3(-uHalf, uBottom, -uHalf), bmax = vec3(uHalf, uLevel, uHalf);
        vec3 t0 = (bmin - ro) / rd, t1 = (bmax - ro) / rd;
        vec3 tmax3 = max(t0, t1);
        float exitD = min(min(tmax3.x, tmax3.y), tmax3.z);
        float thick = max(0.0, min(sceneDist, exitD) - entry);

        vec3 n = normalize(vNormalW);
        bool top = n.y > 0.7;
        if (top) {
          float e = 0.01;
          float h0 = surface(vWorld.xz);
          n = normalize(vec3(-(surface(vWorld.xz + vec2(e, 0.0)) - h0) / e, 1.0, -(surface(vWorld.xz + vec2(0.0, e)) - h0) / e));
        }

        // Refraction: bend the lookup by the surface normal, but never sample land that is in front.
        vec2 ruv = uv + n.xz * 0.035 * clamp(thick, 0.0, 1.0);
        if (viewZAt(ruv) > vViewZ) ruv = uv;
        vec4 behind = texture2D(tScene, ruv);

        vec3 absorb = mix(uAbsorb, vec3(0.9, 1.1, 1.5), uMud) * 1.7;
        vec3 T = exp(-absorb * thick);
        vec3 scatter = mix(uScatter, vec3(0.42, 0.34, 0.22), uMud);
        float a = 1.0 - (T.r + T.g + T.b) / 3.0;
        vec3 col = behind.rgb * T + scatter * (1.0 - T) * 0.8;
        float alpha = behind.a * ((T.r + T.g + T.b) / 3.0) + a;

        // Fresnel sky reflection and sun glints.
        vec3 v = -rd;
        float fres = 0.02 + 0.98 * pow(1.0 - max(dot(n, v), 0.0), 5.0);
        vec3 r = reflect(rd, n);
        vec3 sky = mix(uSkyHorizon, uSkyTop, smoothstep(0.0, 0.6, r.y));
        col = mix(col, sky, fres * (top ? 0.85 : 0.35));
        alpha = mix(alpha, 1.0, fres * (top ? 0.85 : 0.35));
        float glint = pow(max(dot(r, normalize(uSunDir)), 0.0), top ? 600.0 : 80.0) * (top ? 6.0 : 0.6);
        col += uSunCol * glint;
        alpha = min(1.0, alpha + glint);

        // Foam where the surface meets land in shallow water.
        if (top) {
          vec3 scenePos = ro + rd * min(sceneDist, 1e3);
          float depthBelow = uLevel - scenePos.y;
          float foam = (1.0 - smoothstep(0.0, 0.045, depthBelow)) * smoothstep(0.35, 0.75, wNoise(vWorld.xz * 16.0 + uTime * 0.6));
          col = mix(col, vec3(0.97, 0.98, 0.96), foam * 0.75 * (1.0 - uMud * 0.6));
          alpha = max(alpha, foam * 0.75);
        }
        // Edges of the block catch the light like glass.
        float rim = top ? smoothstep(uHalf - 0.08, uHalf - 0.01, max(abs(vWorld.x), abs(vWorld.z))) : 0.0;
        col += vec3(0.9, 0.97, 1.0) * rim * 0.35;
        gl_FragColor = vec4(col, clamp(alpha, 0.0, 1.0));
      }`,
  });
}

function waterGeometry(level: number) {
  const h = Math.max(0.05, level - BOTTOM);
  const g = new RoundedBoxGeometry(2 * HALF, h, 2 * HALF, 5, Math.min(0.26, h * 0.45));
  g.translate(0, BOTTOM + h / 2, 0);
  return g;
}

const COPY_SHADER = {
  uniforms: { tSrc: { value: null as THREE.Texture | null } },
  vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }",
  fragmentShader: "uniform sampler2D tSrc; varying vec2 vUv; void main(){ gl_FragColor = texture2D(tSrc, vUv); }",
};

const FINAL_SHADER = {
  uniforms: { tSrc: { value: null as THREE.Texture | null }, uRes: { value: new THREE.Vector2(1, 1) }, uTilt: { value: 1 } },
  vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }",
  fragmentShader: /* glsl */ `
    uniform sampler2D tSrc; uniform vec2 uRes; uniform float uTilt;
    varying vec2 vUv;
    void main() {
      // Tilt-shift: sharp through the middle of the diorama, soft toward the top and bottom.
      float d = smoothstep(0.18, 0.5, abs(vUv.y - 0.5)) * uTilt;
      vec2 px = d * 2.2 / uRes;
      vec4 c = texture2D(tSrc, vUv) * 0.2270;
      c += (texture2D(tSrc, vUv + vec2(px.x, 0.0)) + texture2D(tSrc, vUv - vec2(px.x, 0.0))) * 0.1945;
      c += (texture2D(tSrc, vUv + vec2(0.0, px.y)) + texture2D(tSrc, vUv - vec2(0.0, px.y))) * 0.1945;
      c += (texture2D(tSrc, vUv + px * 1.8) + texture2D(tSrc, vUv - px * 1.8)) * 0.0945;
      // The scene is premultiplied: tone-map the colour, keep the coverage.
      vec3 rgb = c.a > 0.0001 ? c.rgb / c.a : vec3(0.0);
      gl_FragColor = vec4(rgb, 1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
      gl_FragColor = vec4(gl_FragColor.rgb * c.a, c.a);
    }`,
};

// ---------- main ----------

export async function createDiorama(canvas: HTMLCanvasElement, opts: DioramaOptions): Promise<DioramaHandle | null> {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, premultipliedAlpha: true, powerPreference: "high-performance" });
  } catch {
    return null;
  }
  if (!renderer.capabilities.isWebGL2) {
    renderer.dispose();
    return null;
  }
  // One label per build step below; each is shown while that step runs.
  const steps = [
    "Membentuk bukit dan petak sawah",
    "Menyiapkan alas diorama",
    "Menanam padi",
    "Menumbuhkan hutan",
    "Membangun kampung",
    "Mengalirkan air",
    "Menyalakan matahari",
    "Membuka tirai",
  ];
  let done = 0;
  const progress = async () => {
    opts.onProgress?.(++done, steps.length, steps[Math.min(done, steps.length - 1)]);
    await nextFrame();
  };
  opts.onProgress?.(0, steps.length, steps[0]);
  await nextFrame();

  const dpr = Math.min(window.devicePixelRatio, opts.mobile ? 1.5 : 2);
  renderer.setPixelRatio(dpr);
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(opts.mobile ? 34 : 26, 1, 0.5, 120);
  const r = rng(20261028);

  const landU: LandUniforms = { uLevel: { value: BOTTOM }, uTime: { value: 0 }, uDry: { value: 0 }, uWet: { value: 1 }, uFlood: { value: 0 } };
  const riceU = { uStage: { value: 1.2 }, uDry: landU.uDry, uTime: landU.uTime };

  // 1. Land
  const { terrain, skirt } = buildTerrain(opts.mobile ? 220 : 340);
  const land = new THREE.Mesh(terrain, landMaterial(landU));
  land.receiveShadow = true;
  land.castShadow = true;
  scene.add(land);
  const skirtMesh = new THREE.Mesh(skirt, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1 }));
  scene.add(skirtMesh);
  const slab = new THREE.Mesh(new RoundedBoxGeometry(2 * HALF + 0.3, 0.22, 2 * HALF + 0.3, 4, 0.1), new THREE.MeshStandardMaterial({ color: "#e4d6bb", roughness: 0.9 }));
  slab.position.y = BOTTOM - 0.11;
  slab.receiveShadow = true;
  slab.castShadow = true;
  scene.add(slab);
  await progress();

  // 2. Floor shadow on the page: soft, fading with distance so long low-sun shadows don't streak.
  const floorMat = new THREE.ShadowMaterial({ opacity: 0.22 });
  floorMat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vFloor;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvFloor = position.xy;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vFloor;")
      .replace("gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );", "gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) * (1.0 - smoothstep(6.5, 12.0, length(vFloor))) );");
  };
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = BOTTOM - 0.22;
  floor.receiveShadow = true;
  scene.add(floor);
  const blobTex = (() => {
    const c = document.createElement("canvas");
    c.width = c.height = 128;
    const g = c.getContext("2d")!;
    const grd = g.createRadialGradient(64, 64, 10, 64, 64, 64);
    grd.addColorStop(0, "rgba(60,40,20,0.5)");
    grd.addColorStop(1, "rgba(60,40,20,0)");
    g.fillStyle = grd;
    g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  })();
  const contact = new THREE.Mesh(new THREE.PlaneGeometry(15, 15), new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false }));
  contact.rotation.x = -Math.PI / 2;
  contact.position.y = BOTTOM - 0.215;
  scene.add(contact);
  await progress();

  // 3. Rice
  const ricePos = buildRicePositions(r, opts.mobile ? 6000 : 22000);
  const rice = new THREE.InstancedMesh(riceTuft(), riceMaterial(riceU), ricePos.length);
  const rand = new Float32Array(ricePos.length);
  ricePos.forEach((m, i) => {
    rice.setMatrixAt(i, m);
    rand[i] = r();
  });
  rice.geometry.setAttribute("aRand", new THREE.InstancedBufferAttribute(rand, 1));
  rice.castShadow = !opts.mobile;
  rice.receiveShadow = true;
  scene.add(rice);
  await progress();

  // 4. Forest
  const treePts = buildForest(r, opts.mobile ? 1400 : 3600);
  const trees = new THREE.InstancedMesh(blobGeometry(opts.mobile ? 1 : 2), treeMaterial(landU.uDry), treePts.length);
  const tc = new THREE.Color();
  const dark = new THREE.Color("#22381a"), light = new THREE.Color("#4f7a2e");
  treePts.forEach((t, i) => {
    trees.setMatrixAt(i, new THREE.Matrix4().compose(t.p, new THREE.Quaternion().setFromEuler(new THREE.Euler(0, r() * 6, 0)), new THREE.Vector3(t.s, t.s, t.s)));
    // Neighbour occlusion: crowded blobs sit in shade.
    let near = 0;
    for (let k = Math.max(0, i - 40); k < Math.min(treePts.length, i + 40); k++) if (k !== i && treePts[k].p.distanceToSquared(t.p) < 0.06) near++;
    tc.copy(dark).lerp(light, r() * 0.7 + 0.15).multiplyScalar(1 - Math.min(0.35, near * 0.025));
    trees.setColorAt(i, tc);
  });
  trees.castShadow = true;
  trees.receiveShadow = true;
  scene.add(trees);
  await progress();

  // 5. Village, huts, gate, bridge, palms
  const arch = buildArchitecture(r);
  const archMesh = new THREE.Mesh(arch.solid, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide }));
  archMesh.castShadow = archMesh.receiveShadow = true;
  scene.add(archMesh);
  const glowMat = new THREE.MeshStandardMaterial({ vertexColors: true, emissive: new THREE.Color("#ffb860"), emissiveIntensity: 0 });
  const glowMesh = new THREE.Mesh(arch.glow, glowMat);
  scene.add(glowMesh);
  const lifeMesh = new THREE.Mesh(buildLife(r), archMesh.material);
  lifeMesh.castShadow = lifeMesh.receiveShadow = true;
  scene.add(lifeMesh);
  const boat = new THREE.Mesh(buildBoat(), archMesh.material);
  const boatZ = 2.1;
  boat.position.set(riverX(boatZ), 0, boatZ);
  boat.rotation.y = Math.PI / 2 - Math.atan(Math.cos(boatZ * 0.55 + 0.4) * 0.33);
  boat.scale.setScalar(1.5);
  boat.castShadow = true;
  scene.add(boat);
  const flock = new THREE.Group();
  const wings: THREE.Mesh[] = [];
  {
    const birdMat = new THREE.MeshStandardMaterial({ color: "#f7f5ef", roughness: 0.8, side: THREE.DoubleSide });
    const wing = new THREE.BufferGeometry();
    wing.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0.035, 0, 0, -0.03, 0.15, 0, -0.045, 0, 0, 0.035, 0.15, 0, -0.045, 0.1, 0, 0.01], 3));
    wing.computeVertexNormals();
    const body = new THREE.SphereGeometry(1, 8, 6);
    const formation: [number, number, number][] = [[0, 0, 0], [-0.32, 0.05, -0.3], [0.3, -0.04, -0.32], [-0.62, 0.08, -0.62], [0.6, 0.02, -0.6], [-0.9, -0.03, -0.9], [0.95, 0.06, -0.95]];
    const lead = new THREE.Group();
    lead.position.set(4.2, 3.3, 0);
    formation.forEach(([fx, fy, fz], i) => {
      const bird = new THREE.Group();
      bird.position.set(fx, fy, fz);
      const torso = new THREE.Mesh(body, birdMat);
      torso.scale.set(0.028, 0.024, 0.075);
      bird.add(torso);
      for (const side of [1, -1]) {
        const w = new THREE.Mesh(wing, birdMat);
        w.scale.x = side;
        w.userData.phase = i * 0.7 + (side > 0 ? 0 : 0.0);
        w.userData.side = side;
        bird.add(w);
        wings.push(w);
      }
      lead.add(bird);
    });
    flock.add(lead);
  }
  scene.add(flock);

  // Fish: koi circling the embung, small fish in the river, a school swimming the moat around the block.
  type Fish = { path: "pond" | "river" | "moat"; a: number; speed: number; rad: number; depth: number };
  const fish: Fish[] = [];
  for (let i = 0; i < 14; i++) fish.push({ path: "pond", a: r() * Math.PI * 2, speed: (0.25 + r() * 0.35) * (r() < 0.3 ? -1 : 1), rad: POND.r * (0.3 + r() * 0.55), depth: 0.1 + r() * 0.22 });
  for (let i = 0; i < 7; i++) fish.push({ path: "river", a: r() * Math.PI * 2, speed: 0.12 + r() * 0.12, rad: (r() - 0.5) * 0.25, depth: 0.12 + r() * 0.15 });
  for (let i = 0; i < 22; i++) fish.push({ path: "moat", a: (i / 22) * Math.PI * 2 + r() * 0.15, speed: 0.035 + r() * 0.02, rad: 0.35 + r() * 0.25, depth: 0.08 + r() * 0.16 });
  const fishGeo = (() => {
    const body = new THREE.SphereGeometry(1, 10, 8).scale(0.016, 0.014, 0.05);
    const tail = new THREE.BufferGeometry();
    tail.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, -0.04, 0, 0.022, -0.075, 0, -0.022, -0.075], 3));
    tail.computeVertexNormals();
    return mergeGeometries([body.toNonIndexed().deleteAttribute("uv") as THREE.BufferGeometry, tail], false);
  })();
  const fishMesh = new THREE.InstancedMesh(fishGeo, new THREE.MeshStandardMaterial({ roughness: 0.45, side: THREE.DoubleSide }), fish.length);
  const koi = ["#e8743b", "#f1ede4", "#e2a93b", "#d9542f", "#f1ede4"];
  fish.forEach((f, i) => fishMesh.setColorAt(i, new THREE.Color(f.path === "pond" ? koi[i % koi.length] : f.path === "river" ? "#9aa39b" : i % 3 ? "#c4d3d4" : "#e2b55a")));
  fishMesh.frustumCulled = false;
  scene.add(fishMesh);
  const fishM = new THREE.Matrix4(), fishQ = new THREE.Quaternion(), fishS = new THREE.Vector3(), fishP = new THREE.Vector3(), fishE = new THREE.Euler();
  const moatR = HALF - 0.5;
  /** Position of a fish at angle a on its path. */
  const fishAt = (f: Fish, a: number): [number, number] => {
    if (f.path === "pond") return [POND.x + Math.cos(a) * f.rad, POND.z + Math.sin(a) * f.rad];
    if (f.path === "river") {
      const z = -0.4 + (Math.sin(a) * 0.5 + 0.5) * 4.6;
      return [riverX(z) + f.rad, z];
    }
    // Rounded square loop just inside the block walls.
    const k = (v: number) => Math.sign(v) * Math.pow(Math.abs(v), 0.25);
    const R = moatR - f.rad + 0.25;
    return [R * k(Math.cos(a)), R * k(Math.sin(a))];
  };
  const placeFish = (t: number) => {
    fish.forEach((f, i) => {
      const a = f.a + t * f.speed;
      const [x, z] = fishAt(f, a);
      const [nx, nz] = fishAt(f, a + 0.02 * Math.sign(f.speed));
      const head = Math.atan2(nx - x, nz - z);
      const bed = sampleLand(x, z).h;
      const y = Math.max(bed + 0.04, level - f.depth);
      const visible = y < level - 0.03 && level - bed > 0.08;
      fishP.set(x, y, z);
      fishE.set(0, head + Math.sin(t * 9 + i) * 0.18, 0);
      fishQ.setFromEuler(fishE);
      fishS.setScalar(visible ? (f.path === "river" ? 1 : 1.5) : 0);
      fishM.compose(fishP, fishQ, fishS);
      fishMesh.setMatrixAt(i, fishM);
    });
    fishMesh.instanceMatrix.needsUpdate = true;
  };
  await progress();

  // 6. Water
  const size = new THREE.Vector2();
  const makeRT = (depth: boolean) => {
    const rt = new THREE.WebGLRenderTarget(2, 2, { type: THREE.HalfFloatType, samples: opts.mobile ? 0 : 4 });
    if (depth) rt.depthTexture = new THREE.DepthTexture(2, 2, THREE.FloatType);
    return rt;
  };
  const rtScene = makeRT(true);
  const rtWater = makeRT(false);
  const waterMat = waterMaterial(rtScene);
  let level = BOTTOM + 0.05;
  let levelTarget = LEVEL.normal;
  let builtLevel = level;
  const water = new THREE.Mesh(waterGeometry(level), waterMat);
  const waterScene = new THREE.Scene();
  waterScene.add(water);
  const quadGeo = new THREE.PlaneGeometry(2, 2);
  const copyMat = new THREE.ShaderMaterial({ ...COPY_SHADER, uniforms: THREE.UniformsUtils.clone(COPY_SHADER.uniforms), depthTest: false, depthWrite: false });
  copyMat.uniforms.tSrc.value = rtScene.texture;
  const finalMat = new THREE.ShaderMaterial({ ...FINAL_SHADER, uniforms: THREE.UniformsUtils.clone(FINAL_SHADER.uniforms), depthTest: false, depthWrite: false, transparent: true, premultipliedAlpha: true });
  finalMat.uniforms.tSrc.value = rtWater.texture;
  finalMat.uniforms.uTilt.value = opts.mobile ? 0.6 : 1;
  const copyScene = new THREE.Scene();
  copyScene.add(new THREE.Mesh(quadGeo, copyMat));
  const finalScene = new THREE.Scene();
  finalScene.add(new THREE.Mesh(quadGeo, finalMat));
  const quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  // Rain for floods.
  const rainN = opts.mobile ? 300 : 700;
  const rainGeo = new THREE.BoxGeometry(0.006, 0.22, 0.006);
  const rain = new THREE.InstancedMesh(rainGeo, new THREE.MeshBasicMaterial({ color: "#cfe3ef", transparent: true, opacity: 0.55, depthWrite: false }), rainN);
  const rainY = new Float32Array(rainN).map(() => r() * 4);
  const rainXZ = Array.from({ length: rainN }, () => [(r() * 2 - 1) * (HALF - 0.2), (r() * 2 - 1) * (HALF - 0.2)]);
  rain.visible = false;
  scene.add(rain);
  await progress();

  // 7. Light: a soft sky dome for image-based light and reflections, plus sun and fill.
  const pmrem = new THREE.PMREMGenerator(renderer);
  const skyScene = new THREE.Scene();
  skyScene.add(
    new THREE.Mesh(
      new THREE.SphereGeometry(10, 32, 16),
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        vertexShader: "varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
        fragmentShader: /* glsl */ `
          varying vec3 vD;
          void main() {
            vec3 top = vec3(0.42, 0.62, 0.86), hor = vec3(0.98, 0.93, 0.84), gnd = vec3(0.36, 0.31, 0.22);
            vec3 c = vD.y > 0.0 ? mix(hor, top, pow(vD.y, 0.55)) : mix(hor, gnd, pow(-vD.y, 0.35));
            gl_FragColor = vec4(c, 1.0);
          }`,
      }),
    ),
  );
  const envRT = pmrem.fromScene(skyScene, 0.03);
  pmrem.dispose();
  scene.environment = envRT.texture;
  scene.environmentIntensity = 0.5;
  const hemi = new THREE.HemisphereLight("#cfe2f2", "#a48a62", 1.1);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight("#fff4e0", 2.4);
  sun.castShadow = true;
  sun.shadow.mapSize.set(opts.mobile ? 1024 : 2048, opts.mobile ? 1024 : 2048);
  const sc = sun.shadow.camera;
  sc.left = sc.bottom = -8.5;
  sc.right = sc.top = 8.5;
  sc.near = 1;
  sc.far = 40;
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.02;
  scene.add(sun, sun.target);
  const lamps = [new THREE.PointLight("#ffb45e", 0, 2.2), new THREE.PointLight("#ffb45e", 0, 2.2)];
  lamps[0].position.set(3.7, 0.6, -0.5);
  lamps[1].position.set(3.8, 0.6, 1.0);
  lamps.forEach((l) => scene.add(l));
  await progress();

  // Camera and controls
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.enablePan = false;
  controls.minDistance = 14;
  controls.maxDistance = 34;
  controls.minPolarAngle = 0.35;
  controls.maxPolarAngle = 1.28;
  controls.target.set(0, -0.3, 0);
  // The wheel scrolls the page; on touch screens dragging would trap scrolling, so the view orbits by itself.
  controls.enableZoom = false;
  controls.enabled = !opts.mobile;
  const home = new THREE.Vector3(15.5, 12.5, 17.5).multiplyScalar(opts.mobile ? 0.92 : 1.12);
  const introFrom = home.clone().multiplyScalar(1.45).add(new THREE.Vector3(0, 6, 0));
  camera.position.copy(opts.reducedMotion ? home : introFrom);
  controls.update();

  // State
  // Parallax: the pointer swings the view a few degrees; scrolling lifts the camera and pulls back.
  const pointer = new THREE.Vector2(), pointerS = new THREE.Vector2();
  let scrollP = 0, scrollS = 0;
  const lastOffset = new THREE.Vector3();
  let view: View = { free: true, sx: opts.mobile ? 0 : -0.17, sy: opts.mobile ? -0.12 : 0.02 };
  const shift = { x: view.sx, y: view.sy };
  let vw = 1, vh = 1;
  const sph = new THREE.Spherical();
  const tmpV = new THREE.Vector3();
  let stage = 1.2, stageTarget = 1.2;
  let dry = 0, dryTarget = 0, mud = 0, mudTarget = 0;
  let hour = 14, hourTarget = 14;
  const ripples = waterMat.uniforms.uRipples.value as THREE.Vector4[];
  let rippleI = 0;
  const clock = new THREE.Clock();
  let raf = 0;
  let active = true;
  let introT = opts.reducedMotion ? 1 : 0;
  let frames = 0, fpsT = 0;

  function applyHour(h: number) {
    // 06:00 sunrise to 18:30 sunset, sweeping from east (left) to west.
    const t = THREE.MathUtils.clamp((h - 6) / 12.5, 0, 1);
    const elev = Math.sin(t * Math.PI) * 1.05 + 0.08;
    const az = -1.2 + t * 2.6;
    const dir = new THREE.Vector3(Math.cos(az) * Math.cos(elev), Math.sin(elev), Math.sin(az) * Math.cos(elev) + 0.4).normalize();
    sun.position.copy(dir).multiplyScalar(20);
    const golden = 1 - THREE.MathUtils.smoothstep(Math.sin(t * Math.PI), 0.12, 0.55);
    sun.color.set("#fff4e0").lerp(new THREE.Color("#ff9a52"), golden);
    sun.intensity = 0.5 + 2.0 * THREE.MathUtils.smoothstep(Math.sin(t * Math.PI), 0.0, 0.4);
    hemi.color.set("#cfe2f2").lerp(new THREE.Color("#f2b98f"), golden * 0.7);
    hemi.intensity = 0.38 + 0.42 * Math.sin(t * Math.PI);
    scene.environmentIntensity = 0.12 + 0.16 * Math.sin(t * Math.PI);
    const dusk = THREE.MathUtils.smoothstep(h, 16.8, 18.2);
    glowMat.emissiveIntensity = dusk * 2.4;
    lamps.forEach((l) => (l.intensity = dusk * 1.6));
    waterMat.uniforms.uSunDir.value.copy(dir);
    waterMat.uniforms.uSunCol.value.copy(sun.color).multiplyScalar(0.9);
    (waterMat.uniforms.uSkyHorizon.value as THREE.Color).set("#f3e7d6").lerp(new THREE.Color("#f6c39a"), golden);
    (waterMat.uniforms.uSkyTop.value as THREE.Color).set("#9cc7e6").lerp(new THREE.Color("#c9a6b8"), golden * 0.6);
  }
  applyHour(hour);

  function resize() {
    const w = canvas.clientWidth || 1, h = canvas.clientHeight || 1;
    renderer.setSize(w, h, false);
    renderer.getDrawingBufferSize(size);
    rtScene.setSize(size.x, size.y);
    rtWater.setSize(size.x, size.y);
    waterMat.uniforms.uRes.value.copy(size);
    finalMat.uniforms.uRes.value.copy(size);
    camera.aspect = w / h;
    vw = w;
    vh = h;
    camera.setViewOffset(w, h, shift.x * w, shift.y * h, w, h);
    // Keep the whole block in frame on narrow screens.
    camera.fov = 26 * Math.max(1, 1.3 / Math.max(camera.aspect, 0.5));
    camera.updateProjectionMatrix();
  }
  resize();
  const ro = new ResizeObserver(resize);
  ro.observe(canvas);

  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const onDown = (e: PointerEvent) => {
    const rect = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = new THREE.Vector3();
    if (ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), -level), hit) && Math.abs(hit.x) < HALF && Math.abs(hit.z) < HALF) {
      ripples[rippleI % 6].set(hit.x, hit.z, clock.getElapsedTime(), 1);
      rippleI++;
    }
  };
  canvas.addEventListener("pointerdown", onDown);

  function frame() {
    const dt = Math.min(0.05, clock.getDelta());
    const t = clock.elapsedTime;
    if (!opts.reducedMotion) {
      landU.uTime.value = t;
      waterMat.uniforms.uTime.value = t;
    }
    // Intro: water fills the block while the camera eases in.
    if (introT < 1) {
      introT = Math.min(1, introT + dt / 2.6);
      const e = 1 - Math.pow(1 - introT, 3);
      camera.position.lerpVectors(introFrom, home, e);
    }
    if (opts.mobile && view.free && introT >= 1 && !opts.reducedMotion) {
      camera.position.applyAxisAngle(new THREE.Vector3(0, 1, 0), dt * 0.06);
    }
    // Chapter framing: shift the frame, and outside the hero glide the orbit to the chapter's view.
    const kv = opts.reducedMotion ? 1 : 1 - Math.pow(0.12, dt);
    shift.x += (view.sx - shift.x) * kv;
    shift.y += (view.sy - shift.y) * kv;
    camera.setViewOffset(vw, vh, shift.x * vw, shift.y * vh, vw, vh);
    controls.enabled = !!view.free && !opts.mobile;
    if (!view.free && introT >= 1) {
      camera.position.sub(lastOffset);
      lastOffset.set(0, 0, 0);
      controls.target.y += ((view.ty ?? -0.3) - controls.target.y) * kv;
      sph.setFromVector3(tmpV.copy(camera.position).sub(controls.target));
      let dTheta = (view.theta ?? sph.theta) - sph.theta;
      dTheta = Math.atan2(Math.sin(dTheta), Math.cos(dTheta));
      sph.theta += dTheta * kv;
      sph.phi += (Math.PI / 2 - (view.el ?? 0.5) - sph.phi) * kv;
      sph.radius += ((view.dist ?? 30) - sph.radius) * kv;
      sph.makeSafe();
      camera.position.copy(controls.target).add(tmpV.setFromSpherical(sph));
    }
    const k = opts.reducedMotion ? 1 : 1 - Math.pow(0.02, dt);
    level += (levelTarget - level) * (introT < 1 ? Math.min(1, dt * 1.6) : k * 0.5);
    stage += (stageTarget - stage) * k * 0.6;
    dry += (dryTarget - dry) * k * 0.5;
    mud += (mudTarget - mud) * k * 0.5;
    hour += (hourTarget - hour) * k;
    if (Math.abs(level - builtLevel) > 0.004) {
      water.geometry.dispose();
      water.geometry = waterGeometry(level);
      builtLevel = level;
    }
    landU.uLevel.value = level;
    if (!opts.reducedMotion) {
      flock.rotation.y = -t * 0.09;
      for (const w of wings) w.rotation.z = w.userData.side * Math.sin(t * 7 + w.userData.phase) * 0.55;
    }
    placeFish(opts.reducedMotion ? 0 : t);
    boat.position.y = Math.max(level, -0.5) + 0.012 + (opts.reducedMotion ? 0 : Math.sin(t * 1.3) * 0.006);
    landU.uDry.value = dry;
    landU.uWet.value = (1 - dry) * (1 - THREE.MathUtils.smoothstep(stage, 2.6, 3.2));
    landU.uFlood.value = mud;
    riceU.uStage.value = stage;
    waterMat.uniforms.uLevel.value = level;
    waterMat.uniforms.uMud.value = mud;
    applyHour(hour);

    rain.visible = mud > 0.05;
    if (rain.visible) {
      const m = new THREE.Matrix4();
      for (let i = 0; i < rainN; i++) {
        rainY[i] -= dt * 6.5;
        if (rainY[i] < level) rainY[i] += 4;
        m.makeTranslation(rainXZ[i][0], rainY[i], rainXZ[i][1]);
        rain.setMatrixAt(i, m);
      }
      rain.instanceMatrix.needsUpdate = true;
      (rain.material as THREE.MeshBasicMaterial).opacity = 0.5 * mud;
    }

    // Remove last frame's parallax offset before OrbitControls runs, so its own state stays clean.
    camera.position.sub(lastOffset);
    lastOffset.set(0, 0, 0);
    controls.update();
    if (!opts.reducedMotion) {
      pointerS.lerp(pointer, 1 - Math.pow(0.04, dt));
      scrollS += (scrollP - scrollS) * (1 - Math.pow(0.03, dt));
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      const back = camera.position.clone().sub(controls.target).normalize();
      lastOffset
        .copy(right)
        .multiplyScalar(pointerS.x * 1.1)
        .add(new THREE.Vector3(0, pointerS.y * 0.7 + scrollS * 7, 0))
        .addScaledVector(back, scrollS * 6);
      camera.position.add(lastOffset);
      camera.lookAt(controls.target);
    }
    waterMat.uniforms.uNear.value = camera.near;
    waterMat.uniforms.uFar.value = camera.far;

    renderer.setRenderTarget(rtScene);
    renderer.clear();
    renderer.render(scene, camera);
    renderer.setRenderTarget(rtWater);
    renderer.clear();
    renderer.render(copyScene, quadCam);
    renderer.autoClear = false;
    renderer.render(waterScene, camera);
    renderer.autoClear = true;
    renderer.setRenderTarget(null);
    renderer.clear();
    renderer.render(finalScene, quadCam);

    frames++;
    fpsT += dt;
    if (fpsT > 1) {
      opts.onStats?.(Math.round(frames / fpsT));
      frames = 0;
      fpsT = 0;
    }
    if (active) raf = requestAnimationFrame(frame);
  }
  await progress();
  raf = requestAnimationFrame(frame);

  return {
    setPointer(x, y) {
      pointer.set(x, y);
    },
    setView(v) {
      view = v;
    },
    setScroll(p) {
      scrollP = THREE.MathUtils.clamp(p, 0, 1);
    },
    setWater(m) {
      levelTarget = LEVEL[m];
      dryTarget = m === "kering" ? 1 : 0;
      mudTarget = m === "banjir" ? 1 : 0;
    },
    setStage(s) {
      stageTarget = s;
    },
    setHour(h) {
      hourTarget = h;
    },
    resetView() {
      introFrom.copy(camera.position);
      introT = 0;
      controls.target.set(0, -0.3, 0);
    },
    setActive(on) {
      if (on === active) return;
      active = on;
      if (on) {
        clock.getDelta();
        raf = requestAnimationFrame(frame);
      } else cancelAnimationFrame(raf);
    },
    dispose() {
      active = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener("pointerdown", onDown);
      controls.dispose();
      scene.traverse((o) => {
        const m = o as THREE.Mesh;
        m.geometry?.dispose?.();
        const mat = m.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose());
        else mat?.dispose?.();
      });
      water.geometry.dispose();
      waterMat.dispose();
      envRT.dispose();
      rtScene.dispose();
      rtWater.dispose();
      renderer.dispose();
    },
  };
}
