export type Txt = string | { id: string; en: string };
export const tr = (x: Txt, lang: "id" | "en") => (typeof x === "string" ? x : x[lang]);

export type Polygon = { type: "Polygon"; coordinates: number[][][] };

export type Band = { p5: number[]; p50: number[]; p95: number[] };
export type Rec = { feasibility: number; text: { id: string; en: string }; why: { id: string; en: string }; when?: string | null };
export type Risk = {
  probability: number;
  level: "low" | "medium" | "high";
  physics_probability: number;
  satellite_adjustment: number;
  drivers: Txt[];
  first_stress_day?: { share_of_members: number; p5: number | null; p50: number | null; p95: number | null };
  max_submergence_days?: { p50: number; p95: number; share_any: number };
  river_probability?: number;
};
export type SceneStat = {
  usable: boolean;
  valid_fraction: number;
  ndvi_mean?: number;
  ndwi_mean?: number;
  water_fraction?: number;
};
export type Scene = { scene_id: string; datetime: string; field: SceneStat; neighbours: SceneStat };
export type WaterFeature = {
  osm_id: string;
  kind: string;
  name: string | null;
  intermittent: boolean;
  distance_m: number;
  nearest_point: [number, number];
  geometry: number[][];
};
export type Pest = {
  id: string;
  name: { id: string; en: string };
  level: "low" | "medium" | "high" | "unknown";
  reason: Txt;
  favourable: string;
  reference: string;
  action?: { id: string; en: string };
};

export type Analysis = {
  status: "ok" | "insufficient-data";
  mode: "real" | "test";
  hypothetical: boolean;
  generated_at: string;
  field: { area_ha: number; lat: number; lon: number };
  crop: {
    days_after_transplant: number | null;
    stage: string;
    basis: Txt;
    reliable: boolean;
    transplanting_estimate: { date: string | null; confidence: string; reason: string };
  };
  weather: {
    dates: string[];
    today_index: number;
    rain: (number | null)[];
    et0: (number | null)[];
    tmax: (number | null)[];
    tmin: (number | null)[];
    rh: (number | null)[];
    soil_moisture_now: number | null;
  };
  satellite: {
    series: Scene[];
    latest_clear: Scene | null;
    latest_clear_age_days: number | null;
    scenes_searched: number;
    scenes_usable: number;
    anomalies: {
      signals: { kind: string; weight: number; text: Txt }[];
      vs_neighbours?: { ndvi_diff: number; ndwi_diff: number };
      vs_expected?: { expected: number; observed: number; diff: number };
    };
  };
  terrain: {
    field_elevation_m: number;
    context_min_m: number;
    context_max_m: number;
    mean_slope_deg: number;
    share_of_surroundings_lower: number;
    note: string;
  } | null;
  hand: { height_above_channel_m: number; channel: string; channel_distance_m: number; method: string } | null;
  water_sources: WaterFeature[];
  river: {
    threshold_2y_m3s: number;
    return_5y_m3s: number;
    median_m3s: number;
    forecast_dates: string[];
    forecast_p50: number[];
    forecast_p95: number[];
    exceed_prob_daily: number[];
    exceed_prob: number;
    history_years: number;
    note: string;
  } | null;
  waterbalance: {
    dates: string[];
    members: number;
    ponding: Band;
    depletion: Band;
    ks: Band;
    rain: Band;
    prob_stress: number[];
    prob_severe: number[];
    prob_submerged: number[];
    plant_height_mm: number[];
    first_stress_day: NonNullable<Risk["first_stress_day"]>;
    max_submergence_days: NonNullable<Risk["max_submergence_days"]>;
    initial_state: { ponding_mm: number; depletion_mm: number; basis: Txt[] };
    rain_basis: Txt;
    forecast_days_from_ensemble: number;
    params: Record<string, number | null> & { taw_mm: number; raw_mm: number };
  };
  drought: { risk: Risk; recommendations: Rec[] };
  flood: { risk: Risk; recommendations: Rec[] };
  pest: Pest[];
  confidence: "low" | "medium" | "high";
  sources: { name: string; captured_at: string }[];
  unavailable: { name: string; source: string; reason: string }[];
  disclaimer: Txt;
};

export type Scenario = {
  rain_factor?: number;
  delay_rain_days?: number;
  temp_delta_c?: number;
  extra_rain?: { day: number; mm: number }[];
};

export type AnalyzeOptions = {
  days_after_transplant?: number | null;
  irrigation_mm_day?: number | null;
  initial_ponding_mm?: number | null;
  scenario?: Scenario | null;
};

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!r.ok) {
    let detail = `${r.status}`;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export const api = {
  demoField: async () => (await fetch("/api/demo-field")).json() as Promise<{ name: string; geometry: Polygon; source: string }>,
  validate: (geometry: Polygon) =>
    post<{ valid: boolean; reason?: string; area_ha?: number; lat?: number; lon?: number }>("/api/validate-field", { geometry }),
  analyze: (geometry: Polygon, opts: AnalyzeOptions = {}, signal?: AbortSignal) =>
    post<Analysis>("/api/analyze", { geometry, ...opts }, signal),
  chat: (geometry: Polygon, messages: { role: string; content: string }[], lang: string, dat?: number | null) =>
    post<{ text: string; engine: string; tools_used?: string[]; note?: string }>("/api/chat", {
      geometry,
      messages,
      lang,
      days_after_transplant: dat ?? undefined,
    }),
  health: async () => (await fetch("/api/health")).json(),
};
