import type { Block, Polygon, VerdictSummary } from "./api";

// The officer's list of fields lives in this browser; export/import as GeoJSON moves it elsewhere.
// planting_date, variety and soil are what the P3A chair fills in for TUAI Lancar and Taksir.
export type WatchField = {
  id: string;
  name: string;
  geometry: Polygon;
  dat?: number | null;
  planting_date?: string | null;
  variety?: string | null;
  soil?: string | null;
};
export type Checked = { at: string; result: VerdictSummary };

const KEY = "jagapadi-watchlist";
const RESULTS = "jagapadi-watchlist-results";

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: the list still works for this visit */
  }
}

export const loadFields = () => read<WatchField[]>(KEY, []);
export const saveFields = (f: WatchField[]) => write(KEY, f);
export const loadResults = () => read<Record<string, Checked>>(RESULTS, {});
export const saveResults = (r: Record<string, Checked>) => write(RESULTS, r);

export function addField(f: Omit<WatchField, "id">): WatchField {
  const list = loadFields();
  const same = list.find((x) => JSON.stringify(x.geometry) === JSON.stringify(f.geometry));
  if (same) return same;
  const item = { ...f, id: `f-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}` };
  saveFields([...list, item]);
  return item;
}

export function toGeoJSON(fields: WatchField[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: fields.map((f) => ({
      type: "Feature",
      properties: {
        name: f.name,
        days_after_transplant: f.dat ?? null,
        planting_date: f.planting_date ?? null,
        variety: f.variety ?? null,
        soil: f.soil ?? null,
      },
      geometry: f.geometry,
    })),
  };
}

/** Accepts a FeatureCollection, a Feature or a bare Polygon; MultiPolygons are split into parts. */
export function fromGeoJSON(text: string): Omit<WatchField, "id">[] {
  const data = JSON.parse(text);
  const feats: GeoJSON.Feature[] =
    data.type === "FeatureCollection" ? data.features : data.type === "Feature" ? [data] : [{ type: "Feature", properties: {}, geometry: data }];
  const out: Omit<WatchField, "id">[] = [];
  feats.forEach((f, i) => {
    const name = String(f.properties?.name ?? f.properties?.nama ?? `Petak ${i + 1}`).slice(0, 60);
    const p = f.properties ?? {};
    const dat = typeof p.days_after_transplant === "number" ? p.days_after_transplant : null;
    const date = String(p.planting_date ?? p.tanggal_tanam ?? "");
    const meta = {
      dat,
      planting_date: /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null,
      variety: p.variety ?? p.varietas ?? null,
      soil: p.soil ?? p.tanah ?? null,
    };
    const g = f.geometry;
    if (g?.type === "Polygon") out.push({ name, ...meta, geometry: { type: "Polygon", coordinates: g.coordinates } });
    if (g?.type === "MultiPolygon")
      g.coordinates.forEach((c, j) => out.push({ name: `${name} (${j + 1})`, ...meta, geometry: { type: "Polygon", coordinates: c } }));
  });
  return out;
}

export function updateField(id: string, patch: Partial<Omit<WatchField, "id" | "geometry">>): WatchField[] {
  const list = loadFields().map((f) => (f.id === id ? { ...f, ...patch } : f));
  saveFields(list);
  return list;
}

/** Vertex mean of the outer ring: close enough to the centroid for plots this small. */
export function centerOf(f: { geometry: Polygon }): { lat: number; lon: number } {
  const ring = f.geometry.coordinates[0].slice(0, -1);
  const lon = ring.reduce((a, c) => a + c[0], 0) / ring.length;
  const lat = ring.reduce((a, c) => a + c[1], 0) / ring.length;
  return { lat, lon };
}

export const toBlock = (f: WatchField): Block => ({
  id: f.id,
  name: f.name,
  geometry: f.geometry,
  planting_date: f.planting_date ?? null,
  variety: f.variety ?? null,
  soil: f.soil ?? null,
});
