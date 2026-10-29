import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import maplibregl, { type GeoJSONSource, type Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, API_DOWN, type Polygon, type Status } from "../lib/api";
import { LangToggle, useLang } from "../lib/i18n";
import { Logo } from "../components/Logo";
import { STYLE } from "./FieldMap";
import { addField, fromGeoJSON, loadFields, loadResults, saveFields, saveResults, toGeoJSON, type Checked, type WatchField } from "../lib/watchlist";
import "./app.css";
import "./officer.css";

const T = {
  id: {
    title: "Dasbor penyuluh",
    sub: "Semua petak binaan dalam satu peta, diurutkan dari yang paling berisiko.",
    fields: "petak",
    checkAll: "Periksa semua",
    checking: "Memeriksa",
    sample: "Pakai contoh kelompok tani",
    add: "Tambah petak di peta",
    importG: "Impor GeoJSON",
    exportG: "Ekspor GeoJSON",
    open: "Buka analisis",
    remove: "Hapus",
    never: "belum diperiksa",
    checkedAt: "diperiksa",
    status: { aman: "Aman", waspada: "Waspada", bahaya: "Bahaya" } as Record<Status, string>,
    dry: "kering",
    wet: "terendam",
    emptyT: "Belum ada petak",
    emptyB: "Tambahkan petak dari halaman analisis (tombol Pantau), impor GeoJSON batas petak kelompok tani, atau coba dengan contoh.",
    importErr: "Berkas tidak bisa dibaca sebagai GeoJSON poligon.",
    apiDown: "Server Jagapadi tidak menjawab.",
    noData: "data cuaca tidak tersedia",
    note: "Hasil sama dengan halaman analisis dan peringatan Telegram. Perkiraan ilmiah, bukan peringatan resmi.",
    firstRun: "Petak baru butuh sekitar satu menit; petak di hamparan yang sama memakai ulang citra satelit, jadi lebih cepat.",
  },
  en: {
    title: "Extension officer dashboard",
    sub: "Every field you advise on one map, ranked from most at risk.",
    fields: "fields",
    checkAll: "Check all",
    checking: "Checking",
    sample: "Use a sample farmer group",
    add: "Add a field on the map",
    importG: "Import GeoJSON",
    exportG: "Export GeoJSON",
    open: "Open analysis",
    remove: "Remove",
    never: "not checked yet",
    checkedAt: "checked",
    status: { aman: "Safe", waspada: "Watch", bahaya: "Danger" } as Record<Status, string>,
    dry: "drought",
    wet: "flooding",
    emptyT: "No fields yet",
    emptyB: "Add fields from the analysis page (Watch button), import your farmer group's plot outlines as GeoJSON, or try the sample.",
    importErr: "The file could not be read as GeoJSON polygons.",
    apiDown: "The Jagapadi server is not responding.",
    noData: "weather data unavailable",
    note: "Same results as the analysis page and the Telegram alerts. Scientific estimate, not an official warning.",
    firstRun: "A new field takes about a minute; fields in the same area reuse the satellite scenes, so they are faster.",
  },
};

const ORDER: Record<Status, number> = { bahaya: 0, waspada: 1, aman: 2 };
const COLOR: Record<Status | "none", string> = { bahaya: "#c4571e", waspada: "#e2a93b", aman: "#4f8a3a", none: "#9aa39d" };

function statusOf(c?: Checked): Status | null {
  return c?.result.status === "ok" && c.result.verdict ? c.result.verdict.status : null;
}

export default function Officer() {
  const { lang } = useLang();
  const s = T[lang];
  const nav = useNavigate();
  const [fields, setFields] = useState<WatchField[]>(loadFields);
  const [results, setResults] = useState<Record<string, Checked>>(loadResults);
  const [busy, setBusy] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);

  useEffect(() => saveFields(fields), [fields]);
  useEffect(() => saveResults(results), [results]);

  const ranked = useMemo(
    () =>
      [...fields].sort((a, b) => {
        const sa = statusOf(results[a.id]);
        const sb = statusOf(results[b.id]);
        const oa = sa ? ORDER[sa] : 3;
        const ob = sb ? ORDER[sb] : 3;
        return oa - ob || (results[b.id]?.result.verdict?.probability ?? 0) - (results[a.id]?.result.verdict?.probability ?? 0);
      }),
    [fields, results],
  );
  const counts = useMemo(() => {
    const c: Record<Status, number> = { bahaya: 0, waspada: 0, aman: 0 };
    fields.forEach((f) => {
      const st = statusOf(results[f.id]);
      if (st) c[st] += 1;
    });
    return c;
  }, [fields, results]);

  const check = async (list: WatchField[]) => {
    setError(null);
    setBusy(new Set(list.map((f) => f.id)));
    // Two at a time: enough to overlap network waits without crowding the free data APIs.
    const queue = [...list];
    const worker = async () => {
      for (let f = queue.shift(); f; f = queue.shift()) {
        const cur = f;
        try {
          const r = await api.verdict(cur.geometry, cur.dat);
          setResults((old) => ({ ...old, [cur.id]: { at: new Date().toISOString(), result: r } }));
        } catch (e) {
          setError((e as Error).message === API_DOWN ? s.apiDown : `${cur.name}: ${(e as Error).message}`);
        } finally {
          setBusy((b) => {
            const n = new Set(b);
            n.delete(cur.id);
            return n;
          });
        }
      }
    };
    await Promise.all([worker(), worker()]);
  };

  const useSample = async () => {
    try {
      const g = await api.demoGroup();
      const added = g.fields.map((f) => addField({ name: f.name, geometry: f.geometry }));
      const list = loadFields();
      setFields(list);
      check(added);
    } catch (e) {
      setError((e as Error).message === API_DOWN ? s.apiDown : (e as Error).message);
    }
  };

  const onImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    try {
      const items = fromGeoJSON(await f.text());
      if (!items.length) throw new Error("empty");
      const added = items.map((x) => addField(x));
      setFields(loadFields());
      check(added);
    } catch {
      setError(s.importErr);
    }
  };

  const onExport = () => {
    const blob = new Blob([JSON.stringify(toGeoJSON(fields), null, 1)], { type: "application/geo+json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "jagapadi-petak.geojson";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const remove = (id: string) => {
    setFields((l) => l.filter((f) => f.id !== id));
    setResults((r) => {
      const n = { ...r };
      delete n[id];
      return n;
    });
  };

  const last = Object.values(results)
    .map((r) => r.at)
    .sort()
    .pop();

  return (
    <div className="ws officer">
      <header className="ws-top">
        <Link to="/" className="ws-logo" aria-label="Jagapadi">
          <Logo size={28} />
        </Link>
        <div className="ws-top-right">
          <Link to="/app" className="btn btn-ghost small">
            {s.add}
          </Link>
          <LangToggle />
        </div>
      </header>
      <div className="ws-body">
        <div className="ws-map">
          <GroupMap fields={fields} results={results} sel={sel} onSelect={setSel} />
        </div>
        <aside className="drawer" aria-label={s.title}>
          <header className="off-head">
            <h1>{s.title}</h1>
            <p className="muted small">{s.sub}</p>
            <p className="tabular small">
              {fields.length} {s.fields} · {last ? `${s.checkedAt} ${new Date(last).toLocaleString(lang === "id" ? "id-ID" : "en-GB")}` : s.never}
            </p>
          </header>
          {fields.length > 0 && (
            <div className="tally">
              {(["bahaya", "waspada", "aman"] as Status[]).map((k) => (
                <p key={k} className={`st-${k}`}>
                  <b>{counts[k]}</b>
                  {s.status[k]}
                </p>
              ))}
            </div>
          )}
          <div className="off-tools">
            {fields.length > 0 && (
              <button type="button" className="btn btn-primary small" onClick={() => check(fields)} disabled={busy.size > 0}>
                {busy.size > 0 ? `${s.checking} (${fields.length - busy.size}/${fields.length})` : s.checkAll}
              </button>
            )}
            <button type="button" className="btn btn-ghost small" onClick={() => file.current?.click()}>
              {s.importG}
            </button>
            {fields.length > 0 && (
              <button type="button" className="btn btn-ghost small" onClick={onExport}>
                {s.exportG}
              </button>
            )}
            <input ref={file} type="file" accept=".geojson,.json,application/geo+json" hidden onChange={onImport} />
          </div>
          {error && <p className="error felt">{error}</p>}
          {busy.size > 0 && <p className="muted small">{s.firstRun}</p>}
          {fields.length === 0 ? (
            <div className="empty">
              <img src="/mascot/mascot-waving-256.png" srcSet="/mascot/mascot-waving-256@2x.png 2x" width={160} height={160} alt="" />
              <h2>{s.emptyT}</h2>
              <p>{s.emptyB}</p>
              <div className="empty-ctas">
                <button type="button" className="btn btn-primary" onClick={useSample}>
                  {s.sample}
                </button>
              </div>
            </div>
          ) : (
            <ol className="off-list">
              {ranked.map((f) => {
                const c = results[f.id];
                const v = c?.result.verdict;
                const st = statusOf(c);
                return (
                  <li
                    key={f.id}
                    className={`felt off-row ${sel === f.id ? "on" : ""}`}
                    style={{ ["--st" as string]: COLOR[st ?? "none"] }}
                    onMouseEnter={() => setSel(f.id)}
                  >
                    <div className="off-row-top">
                      <span className="off-badge">{busy.has(f.id) ? `${s.checking}…` : st ? s.status[st] : s.never}</span>
                      <h3>{f.name}</h3>
                      {c?.result.field && <span className="muted tiny tabular">{c.result.field.area_ha} ha</span>}
                    </div>
                    {v ? (
                      <>
                        <p className="off-head-line">{v.headline[lang]}</p>
                        <p className="small off-today">{v.today[lang]}</p>
                        <p className="tiny muted tabular">
                          {Math.round((c.result.drought?.probability ?? 0) * 100)}% {s.dry} · {Math.round((c.result.flood?.probability ?? 0) * 100)}% {s.wet}
                        </p>
                      </>
                    ) : (
                      c && <p className="small muted">{s.noData}</p>
                    )}
                    <div className="off-actions">
                      <button type="button" className="link" onClick={() => nav("/app", { state: { geometry: f.geometry, name: f.name, dat: f.dat ?? null } })}>
                        {s.open}
                      </button>
                      <button type="button" className="link muted" onClick={() => remove(f.id)}>
                        {s.remove}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
          <p className="disclaimer">{s.note}</p>
        </aside>
      </div>
    </div>
  );
}

function GroupMap({
  fields,
  results,
  sel,
  onSelect,
}: {
  fields: WatchField[];
  results: Record<string, Checked>;
  sel: string | null;
  onSelect: (id: string) => void;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const [ready, setReady] = useState(false);
  const fitted = useRef(0);

  useEffect(() => {
    if (!el.current) return;
    const m = new maplibregl.Map({ container: el.current, style: STYLE, center: [105.3356, -5.0998], zoom: 13, attributionControl: { compact: true } });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    m.on("load", () => {
      m.addSource("fields", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "f-fill", type: "fill", source: "fields", paint: { "fill-color": ["get", "color"], "fill-opacity": 0.5 } });
      m.addLayer({
        id: "f-line",
        type: "line",
        source: "fields",
        paint: { "line-color": ["case", ["get", "sel"], "#ffffff", ["get", "color"]], "line-width": ["case", ["get", "sel"], 3.5, 2] },
      });
      m.addLayer({
        id: "f-label",
        type: "symbol",
        source: "fields",
        layout: { "text-field": ["get", "name"], "text-size": 12, "text-font": ["Open Sans Semibold"] },
        paint: { "text-color": "#ffffff", "text-halo-color": "#1b2a23", "text-halo-width": 1.4 },
      });
      m.on("click", "f-fill", (e) => {
        const id = e.features?.[0]?.properties?.id;
        if (id) onSelect(String(id));
      });
      m.on("mouseenter", "f-fill", () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", "f-fill", () => (m.getCanvas().style.cursor = ""));
      setReady(true);
    });
    map.current = m;
    return () => m.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    const features = fields.map((f) => ({
      type: "Feature" as const,
      properties: { id: f.id, name: f.name, color: COLOR[statusOf(results[f.id]) ?? "none"], sel: f.id === sel },
      geometry: f.geometry as Polygon,
    }));
    (m.getSource("fields") as GeoJSONSource).setData({ type: "FeatureCollection", features });
    // Fit once whenever the number of fields changes, not on every status update.
    if (fields.length && fitted.current !== fields.length) {
      fitted.current = fields.length;
      const b = new maplibregl.LngLatBounds();
      fields.forEach((f) => f.geometry.coordinates[0].forEach((c) => b.extend(c as [number, number])));
      m.fitBounds(b, { padding: 60, maxZoom: 17, duration: 600 });
    }
  }, [fields, results, sel, ready]);

  return <div ref={el} className="field-map" role="application" aria-label="Peta petak / fields map" />;
}
