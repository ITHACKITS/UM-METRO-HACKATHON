import type { Polygon, VerdictSummary } from "./api";

// The officer's list of fields lives in this browser; export/import as GeoJSON moves it elsewhere.
export type WatchField = { id: string; name: string; geometry: Polygon; dat?: number | null };
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
    features: fields.map((f) => ({ type: "Feature", properties: { name: f.name, days_after_transplant: f.dat ?? null }, geometry: f.geometry })),
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
    const dat = typeof f.properties?.days_after_transplant === "number" ? f.properties.days_after_transplant : null;
    const g = f.geometry;
    if (g?.type === "Polygon") out.push({ name, dat, geometry: { type: "Polygon", coordinates: g.coordinates } });
    if (g?.type === "MultiPolygon")
      g.coordinates.forEach((c, j) => out.push({ name: `${name} (${j + 1})`, dat, geometry: { type: "Polygon", coordinates: c } }));
  });
  return out;
}
