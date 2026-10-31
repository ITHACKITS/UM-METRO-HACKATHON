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
  ndmi_mean?: number;
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

export type Bi = { id: string; en: string };
export type Status = "aman" | "waspada" | "bahaya";
export type Verdict = {
  status: Status;
  threat: "drought" | "flood" | "pest" | null;
  probability: number;
  headline: Bi;
  why: Bi;
  today: Bi;
  confidence: "low" | "medium" | "high";
};
export type VerdictSummary = {
  status: "ok" | "insufficient-data";
  field: { area_ha: number; lat: number; lon: number };
  verdict?: Verdict;
  drought?: Pick<Risk, "probability" | "level" | "first_stress_day">;
  flood?: Pick<Risk, "probability" | "level" | "max_submergence_days">;
  pest_high?: Bi[];
  stage?: string;
  scene_age_days?: number | null;
  generated_at?: string;
};

export type BmkgDay = { date: string; rain_mm: number; max_3h_mm: number; weather: string[]; category: Bi | null };
export type SiagaWarning = { kind: "heavy_rain" | "flooded" | "submergence_forecast"; level: "medium" | "high"; date: string | null; text: Bi };
export type Siaga = {
  level: "low" | "medium" | "high";
  warnings: SiagaWarning[];
  bmkg: { area: { adm4: string; desa: string; kecamatan: string; kotkab: string; distance_km: number }; days: BmkgDay[]; captured_at: string; source: string } | null;
  radar_flood: {
    flooded_now: boolean;
    since: string | null;
    days_observed: number;
    passes: number;
    puddling_stage: boolean;
    slope_masked: boolean;
    history: { date: string; orbit: string; vv_db: number; reference_db: number; ratio: number; flooded: boolean }[];
    method: Bi;
  } | null;
  damage_threshold_days: number;
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
      vs_neighbours?: { ndvi_diff: number; ndmi_diff: number };
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
  radar: {
    latest: { datetime: string; orbit: string; field: { usable: boolean; vv_db_mean?: number; water_fraction?: number } };
    latest_age_days: number;
    ring_water_now: number | null;
    ring_water_median: number | null;
    scenes: number;
    flood_signal: boolean;
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
  siaga?: Siaga;
  confidence: "low" | "medium" | "high";
  sources: { name: string; captured_at: string }[];
  unavailable: { name: string; source: string; reason: string }[];
  disclaimer: Txt;
  verdict: Verdict;
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

// TUAI blocks: a field the P3A chair has described.
export type Block = {
  id: string;
  name?: string;
  geometry: Polygon;
  planting_date?: string | null;
  variety?: string | null;
  soil?: string | null;
};

export type LancarRow = {
  id: string;
  name: string | null;
  rank: number;
  color: "merah" | "kuning" | "hijau";
  flowering: boolean;
  days_after_transplant: number | null;
  stage: string;
  need_mm_7d: number;
  need_m3_7d: number;
  area_ha: number;
  prob_stress_7d: number;
  first_stress_p50: number | null;
  calc_bad: boolean;
  pantau_bad: boolean;
  pantau_known: boolean;
  soil: { class: string; name: Bi; basis: Bi } | null;
  reasons: Bi[];
  check_field: boolean;
};
export type LancarResult = { generated_at: string; order: LancarRow[]; skipped: { id: string; name: string | null; reason: string }[]; rule: Bi };
export type Decision = {
  season: string;
  block_id: string;
  block_name?: string | null;
  date: string;
  decision: string;
  outcome: string;
  followed_recommendation?: boolean | null;
  by: string;
  recorded_at?: string;
};

export type TaksirRow = {
  id: string;
  name: string | null;
  area_ha: number;
  features: { ndvi: number | null; ndmi: number | null; events: number; event_text: Bi[]; scenes: number; window: string };
  class: "di_bawah" | "sekitar" | "di_atas" | null;
  class_reason: Bi;
  score?: number;
  estimate?: { t_ha: number; low: number; high: number } | null;
};
export type TaksirResult = {
  generated_at: string;
  mode: "class" | "regression";
  model: { n: number; seasons: string[]; rmse_t_ha: number; r2_in_sample: number; coef: Record<string, number> } | null;
  blocks: TaksirRow[];
  skipped: { id: string; name: string | null; reason: string }[];
  harvest_records: number;
  needs: { records: number; seasons: number };
  note: Bi;
};

export type SigapPart = "daun" | "pangkal" | "gejala";
export type SigapClass = { key: string; name: Bi; kind: string; advice: Bi; checked_by_ppl: boolean; source: string };
export type SigapBox = { x: number; y: number; w: number; h: number; confidence: number; class: string };
type ModelOut = { status: "ok" | "unavailable"; reason?: string; model?: string };
export type SigapResult = {
  part: SigapPart;
  finding: { key: string; label: string; confidence: number; count?: number } | null;
  needs_review: boolean;
  review_reasons: Bi[];
  models: {
    disease?: ModelOut & { ranked?: { key: string; confidence: number }[] };
    symptoms?: ModelOut & { ranked?: { key: string; confidence: number }[] };
    planthopper?: ModelOut & { boxes?: SigapBox[]; count?: number; note?: Bi };
  };
  advice: SigapClass | null;
};
export type SigapReport = {
  id: string;
  created_at: string;
  status: "pending" | "verified" | "rejected";
  lat: number;
  lon: number;
  label: string;
  kind: string;
  source: "foto" | "laporan_cepat";
  confidence?: number | null;
  count?: number | null;
  severity?: "ringan" | "sedang" | "berat" | null;
  needs_review: boolean;
  block_id?: string | null;
  block_name?: string | null;
  reporter?: string | null;
  note?: string | null;
  photo: boolean;
  review: { by: string; at: string; note: string; original_label: string } | null;
};
export type SigapStatus = {
  disease: { model: string; state: string };
  planthopper: { state: string };
  symptoms: { state: string };
  review_below: number;
  classes: Record<string, SigapClass>;
};
export type SigapWarnings = {
  blocks: Record<string, { warning: boolean; counts: Record<string, number>; triggered: string[] }>;
  rule: { radius_m: number; min_reports: number; days: number; labels: string[] };
  note: Bi;
};

// Thrown when the backend cannot be reached (network failure, or the dev proxy's bare 5xx).
export const API_DOWN = "api-down";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, init);
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new Error(API_DOWN);
  }
  if (!r.ok) {
    let detail = r.status >= 500 ? API_DOWN : `${r.status}`;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

const post = <T,>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });

export const api = {
  demoField: () => request<{ name: string; geometry: Polygon; source: string }>("/api/demo-field"),
  demoGroup: () => request<{ name: string; source: string; fields: { id: string; name: string; geometry: Polygon }[] }>("/api/demo-group"),
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
  verdict: (geometry: Polygon, dat?: number | null) =>
    post<VerdictSummary>("/api/verdict", { geometry, days_after_transplant: dat ?? undefined }),
  alertSubscribe: (geometry: Polygon, name: string, lang: string, dat?: number | null) =>
    post<{ enabled: boolean; code?: string; link?: string | null }>("/api/alerts/subscribe", {
      geometry,
      name,
      lang,
      days_after_transplant: dat ?? undefined,
    }),
  lancar: (blocks: Block[]) => post<LancarResult>("/api/lancar/rank", { blocks }),
  decide: (d: Decision) => post<Decision>("/api/lancar/decisions", d),
  decisions: (season?: string) => request<{ decisions: Decision[] }>(`/api/lancar/decisions${season ? `?season=${encodeURIComponent(season)}` : ""}`),
  taksir: (blocks: Block[]) => post<TaksirResult>("/api/taksir", { blocks }),
  harvest: (block: Block, season: string, yield_t_ha: number) => post<unknown>("/api/taksir/harvest", { block, season, yield_t_ha }),
  sigapStatus: () => request<SigapStatus>("/api/sigap/status"),
  sigapAnalyze: (image: string, part: SigapPart) => post<SigapResult>("/api/sigap/analyze", { image, part }),
  sigapReport: (r: Partial<SigapReport> & { lat: number; lon: number; label: string; image?: string | null }) => post<SigapReport>("/api/sigap/reports", r),
  sigapReports: (days = 60) => request<{ reports: SigapReport[] }>(`/api/sigap/reports?days=${days}`),
  sigapReview: (id: string, body: { status: "verified" | "rejected"; label?: string; reviewer: string; note?: string; pin?: string }) =>
    post<SigapReport>(`/api/sigap/reports/${id}/review`, body),
  sigapWarnings: (blocks: { id: string; lat: number; lon: number }[]) => post<SigapWarnings>("/api/sigap/warnings", { blocks }),
  health: () => request<{ telegram: boolean; llm: boolean; offline_replay: boolean }>("/api/health"),
};
