import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import maplibregl, { type GeoJSONSource, type Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, API_DOWN, type SigapPart, type SigapReport, type SigapResult, type SigapStatus, type SigapWarnings } from "../lib/api";
import { LangToggle, useLang } from "../lib/i18n";
import { Logo } from "../components/Logo";
import { STYLE } from "./FieldMap";
import { centerOf, loadFields, type WatchField } from "../lib/watchlist";
import "./app.css";
import "./officer.css";
import "./sigap.css";

const T = {
  id: {
    title: "TUAI Sigap",
    sub: "Foto daun atau pangkal rumpun, AI mengenali penyakit dan hama. Laporan yang sudah dicek PPL masuk peta sebaran desa.",
    tabPhoto: "Foto",
    tabRat: "Lapor tikus",
    tabPpl: "Cek PPL",
    part: { daun: "Daun", pangkal: "Pangkal rumpun", gejala: "Gejala lain" } as Record<SigapPart, string>,
    partHint: {
      daun: "Satu daun bergejala, dekat, latar polos bila bisa.",
      pangkal: "Pangkal batang dekat air, tempat wereng coklat hidup.",
      gejala: "Batang mati (sundep), malai hampa (beluk), daun terkikis atau terlipat.",
    } as Record<SigapPart, string>,
    pick: "Ambil atau pilih foto",
    again: "Foto lain",
    reading: "AI sedang membaca foto…",
    where: "Lokasi",
    whereHint: "Pilih petak, pakai lokasi HP, atau ketuk peta.",
    myLoc: "Lokasi saya",
    noBlock: "Pilih petak…",
    noLoc: "Lokasi belum dipilih",
    conf: "keyakinan",
    review: "Perlu dicek PPL",
    reviewOk: "Cukup yakin, tetap dicek PPL sebelum masuk peta",
    count: (n: number) => `${n} wereng terlihat di foto`,
    advice: "Saran awal",
    draft: "Draf, belum dicek PPL. Sistem tidak menyuruh menyemprot.",
    label: "Hasil yang dilaporkan",
    send: "Kirim laporan",
    sent: "Terkirim. Menunggu cek PPL.",
    models: "Model",
    unavailable: "belum tersedia",
    severity: "Tingkat kerusakan",
    sev: { ringan: "Ringan", sedang: "Sedang", berat: "Berat" },
    note: "Catatan (opsional)",
    ratWhy: "Tikus tidak ada di dataset foto, jadi dicatat lewat laporan cepat. Tetap penting: penyebab puso terluas di antara hama padi 2024 (1.205 ha).",
    pin: "PIN PPL",
    reviewer: "Nama pemeriksa",
    verify: "Benar",
    reject: "Tolak",
    pending: "Menunggu dicek",
    none: "Tidak ada laporan yang menunggu.",
    recent: "Sudah dicek",
    status: { pending: "menunggu", verified: "terverifikasi", rejected: "ditolak" },
    warnT: "Peringatan blok sekitar",
    warnNone: "Belum ada blok yang terkena peringatan.",
    warnRule: (r: SigapWarnings["rule"]) => `Pemicu: minimal ${r.min_reports} laporan ${r.labels.join("/")} terverifikasi dalam ${r.radius_m} m selama ${r.days} hari.`,
    apiDown: "Server TUAI tidak menjawab.",
    legend: ["terverifikasi", "menunggu cek"],
  },
  en: {
    title: "TUAI Sigap",
    sub: "Photograph a leaf or the base of a hill and the AI names the disease or pest. Reports checked by the PPL go on the village map.",
    tabPhoto: "Photo",
    tabRat: "Report rats",
    tabPpl: "PPL check",
    part: { daun: "Leaf", pangkal: "Base of hill", gejala: "Other symptom" } as Record<SigapPart, string>,
    partHint: {
      daun: "One affected leaf, close up, plain background if possible.",
      pangkal: "The stem base near the water, where brown planthoppers live.",
      gejala: "Dead centre shoot (deadheart), empty panicle (whitehead), scraped or folded leaves.",
    } as Record<SigapPart, string>,
    pick: "Take or choose a photo",
    again: "Another photo",
    reading: "The AI is reading the photo…",
    where: "Location",
    whereHint: "Pick a plot, use the phone location, or tap the map.",
    myLoc: "My location",
    noBlock: "Pick a plot…",
    noLoc: "No location yet",
    conf: "confidence",
    review: "PPL check needed",
    reviewOk: "Fairly sure; the PPL still checks it before it goes on the map",
    count: (n: number) => `${n} planthoppers seen in the photo`,
    advice: "First advice",
    draft: "Draft, not yet checked by the PPL. The system never tells you to spray.",
    label: "Reported result",
    send: "Send report",
    sent: "Sent. Waiting for the PPL check.",
    models: "Models",
    unavailable: "not available yet",
    severity: "Damage level",
    sev: { ringan: "Light", sedang: "Moderate", berat: "Heavy" },
    note: "Note (optional)",
    ratWhy: "Rats are not in the photo datasets, so they are logged with a quick report. They still matter: the largest crop-failure area among rice pests in 2024 (1,205 ha).",
    pin: "PPL PIN",
    reviewer: "Checked by",
    verify: "Correct",
    reject: "Reject",
    pending: "Waiting for check",
    none: "No reports waiting.",
    recent: "Checked",
    status: { pending: "pending", verified: "verified", rejected: "rejected" },
    warnT: "Warnings for nearby blocks",
    warnNone: "No block has a warning yet.",
    warnRule: (r: SigapWarnings["rule"]) => `Trigger: at least ${r.min_reports} verified ${r.labels.join("/")} reports within ${r.radius_m} m over ${r.days} days.`,
    apiDown: "The TUAI server is not responding.",
    legend: ["verified", "waiting for check"],
  },
};

type Loc = { lat: number; lon: number; block?: WatchField | null };
type Tab = "photo" | "rat" | "ppl";

/**
 * Downscale on the phone before upload: field photos are often 4000 px and several MB.
 * Pixels are kept as stored, without the browser's colour management: the models were
 * trained on unmanaged pixels, and a photo with an ICC profile otherwise shifted from
 * blast 83% to brown spot 53%.
 */
async function shrink(file: File, max = 1280): Promise<string> {
  const bm = await createImageBitmap(file, { colorSpaceConversion: "none", imageOrientation: "from-image" });
  const k = Math.min(1, max / Math.max(bm.width, bm.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bm.width * k);
  c.height = Math.round(bm.height * k);
  c.getContext("2d")!.drawImage(bm, 0, 0, c.width, c.height);
  bm.close();
  return c.toDataURL("image/jpeg", 0.85);
}

export default function Sigap() {
  const { lang } = useLang();
  const s = T[lang];
  const [tab, setTab] = useState<Tab>("photo");
  const [status, setStatus] = useState<SigapStatus | null>(null);
  const [reports, setReports] = useState<SigapReport[]>([]);
  const [warnings, setWarnings] = useState<SigapWarnings | null>(null);
  const [loc, setLoc] = useState<Loc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const blocks = useMemo(loadFields, []);

  const fail = (e: unknown) => setError((e as Error).message === API_DOWN ? s.apiDown : (e as Error).message);

  const refresh = async () => {
    try {
      const r = await api.sigapReports(60);
      setReports(r.reports);
      if (blocks.length) setWarnings(await api.sigapWarnings(blocks.map((b) => ({ id: b.id, ...centerOf(b) }))));
    } catch (e) {
      fail(e);
    }
  };

  useEffect(() => {
    api.sigapStatus().then(setStatus).catch(fail);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const name = (key: string) => status?.classes[key]?.name[lang] ?? key;
  const pending = reports.filter((r) => r.status === "pending");

  return (
    <div className="ws officer sigap">
      <header className="ws-top">
        <Link to="/" className="ws-logo" aria-label="TUAI">
          <Logo size={28} />
        </Link>
        <div className="ws-top-right">
          <Link to="/ppl" className="btn btn-ghost small">
            P3A / PPL
          </Link>
          <LangToggle />
        </div>
      </header>
      <div className="ws-body">
        <div className="ws-map">
          <ReportMap reports={reports} blocks={blocks} warnings={warnings} loc={loc} onPick={(lat, lon) => setLoc({ lat, lon, block: null })} name={name} legend={s.legend} />
        </div>
        <aside className="drawer" aria-label={s.title}>
          <header className="off-head">
            <h1>{s.title}</h1>
            <p className="muted small">{s.sub}</p>
          </header>
          <nav className="seg sg-tabs" role="tablist">
            {(["photo", "rat", "ppl"] as Tab[]).map((k) => (
              <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>
                {k === "photo" ? s.tabPhoto : k === "rat" ? s.tabRat : `${s.tabPpl}${pending.length ? ` (${pending.length})` : ""}`}
              </button>
            ))}
          </nav>
          {error && <p className="error felt">{error}</p>}
          {tab !== "ppl" && <Where s={s} loc={loc} setLoc={setLoc} blocks={blocks} />}
          {tab === "photo" && <PhotoTab s={s} loc={loc} status={status} name={name} onSent={refresh} fail={fail} />}
          {tab === "rat" && <RatTab s={s} loc={loc} onSent={refresh} fail={fail} />}
          {tab === "ppl" && <PplTab s={s} reports={reports} name={name} status={status} onDone={refresh} fail={fail} />}
          {warnings && (
            <section className="felt pad sg-warn">
              <h3>{s.warnT}</h3>
              {Object.entries(warnings.blocks).filter(([, w]) => w.warning).length === 0 ? (
                <p className="small muted">{s.warnNone}</p>
              ) : (
                <ul>
                  {Object.entries(warnings.blocks)
                    .filter(([, w]) => w.warning)
                    .map(([id, w]) => (
                      <li key={id}>
                        <b>{blocks.find((b) => b.id === id)?.name ?? id}</b>: {w.triggered.map((k) => `${name(k)} (${w.counts[k]})`).join(", ")}
                      </li>
                    ))}
                </ul>
              )}
              <p className="tiny muted">
                {s.warnRule(warnings.rule)} {warnings.note[lang]}
              </p>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

type S = (typeof T)["id"];

function Where({ s, loc, setLoc, blocks }: { s: S; loc: Loc | null; setLoc: (l: Loc) => void; blocks: WatchField[] }) {
  const [busy, setBusy] = useState(false);
  const mine = () => {
    if (!navigator.geolocation) return;
    setBusy(true);
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setLoc({ lat: p.coords.latitude, lon: p.coords.longitude, block: null });
        setBusy(false);
      },
      () => setBusy(false),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  };
  return (
    <section className="sg-where">
      <p className="tiny muted">
        <b>{s.where}</b> · {s.whereHint}
      </p>
      <div className="sg-where-row">
        {blocks.length > 0 && (
          <select
            value={loc?.block?.id ?? ""}
            onChange={(e) => {
              const b = blocks.find((x) => x.id === e.target.value);
              if (b) setLoc({ ...centerOf(b), block: b });
            }}
          >
            <option value="">{s.noBlock}</option>
            {blocks.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        )}
        <button type="button" className="btn btn-ghost small" onClick={mine} disabled={busy}>
          {s.myLoc}
        </button>
      </div>
      <p className="tiny tabular">{loc ? `${loc.block ? `${loc.block.name} · ` : ""}${loc.lat.toFixed(5)}, ${loc.lon.toFixed(5)}` : s.noLoc}</p>
    </section>
  );
}

function PhotoTab({
  s,
  loc,
  status,
  name,
  onSent,
  fail,
}: {
  s: S;
  loc: Loc | null;
  status: SigapStatus | null;
  name: (k: string) => string;
  onSent: () => void;
  fail: (e: unknown) => void;
}) {
  const { lang } = useLang();
  const [part, setPart] = useState<SigapPart>("daun");
  const [img, setImg] = useState<string | null>(null);
  const [res, setRes] = useState<SigapResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [label, setLabel] = useState("");
  const [sent, setSent] = useState(false);
  const file = useRef<HTMLInputElement>(null);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setRes(null);
    setSent(false);
    setBusy(true);
    try {
      const data = await shrink(f);
      setImg(data);
      const r = await api.sigapAnalyze(data, part);
      setRes(r);
      setLabel(r.finding?.key ?? "");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  };

  const send = async () => {
    if (!loc || !label || !img) return;
    try {
      await api.sigapReport({
        lat: loc.lat,
        lon: loc.lon,
        label,
        source: "foto",
        confidence: res?.finding?.key === label ? res.finding.confidence : null,
        count: label === "wereng" ? res?.models.planthopper?.count ?? null : null,
        needs_review: res?.needs_review ?? true,
        block_id: loc.block?.id ?? null,
        block_name: loc.block?.name ?? null,
        image: img,
      });
      setSent(true);
      onSent();
    } catch (err) {
      fail(err);
    }
  };

  const boxes = res?.models.planthopper?.boxes ?? [];
  const f = res?.finding;
  return (
    <>
      <div className="seg sg-part" role="radiogroup">
        {(["daun", "pangkal", "gejala"] as SigapPart[]).map((p) => (
          <button key={p} type="button" role="radio" aria-checked={part === p} className={part === p ? "on" : ""} onClick={() => setPart(p)}>
            {s.part[p]}
          </button>
        ))}
      </div>
      <p className="small muted">{s.partHint[part]}</p>
      <input ref={file} type="file" accept="image/*" capture="environment" hidden onChange={onFile} />
      <button type="button" className="btn btn-primary" onClick={() => file.current?.click()} disabled={busy}>
        {img ? s.again : s.pick}
      </button>
      {img && (
        <figure className="sg-photo">
          <img src={img} alt="" />
          {boxes.map((b, i) => (
            <span key={i} className="sg-box" style={{ left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.w * 100}%`, height: `${b.h * 100}%` }} />
          ))}
        </figure>
      )}
      {busy && <p className="small muted">{s.reading}</p>}
      {res && (
        <section className="felt pad sg-result">
          {f ? (
            <>
              <div className="sg-result-top">
                <h3>{name(f.key)}</h3>
                <span className="tabular small">
                  {Math.round(f.confidence * 100)}% {s.conf}
                </span>
              </div>
              {f.key === "wereng" && f.count != null && <p className="small">{s.count(f.count)}</p>}
              {res.models.planthopper?.note && <p className="tiny muted">{res.models.planthopper.note[lang]}</p>}
            </>
          ) : null}
          <p className={`sg-flag ${res.needs_review ? "warn-flag" : "ok-flag"}`}>
            {res.needs_review ? `${s.review}: ${res.review_reasons.map((r) => r[lang]).join("; ")}` : s.reviewOk}
          </p>
          {res.advice && (
            <>
              <h4>{s.advice}</h4>
              <p className="small">{res.advice.advice[lang]}</p>
              <p className="tiny muted">{s.draft}</p>
            </>
          )}
          <details className="tiny">
            <summary>{s.models}</summary>
            <ul>
              {Object.entries(res.models).map(([k, m]) => (
                <li key={k}>
                  <b>{k}</b>: {m.status === "ok" ? m.model : `${s.unavailable} (${m.reason})`}
                </li>
              ))}
            </ul>
          </details>
          <label className="sg-field">
            <span className="tiny muted">{s.label}</span>
            <select value={label} onChange={(e) => setLabel(e.target.value)}>
              <option value="" />
              {status &&
                Object.values(status.classes).map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.name[lang]}
                  </option>
                ))}
            </select>
          </label>
          {sent ? (
            <p className="small ok-flag sg-flag">{s.sent}</p>
          ) : (
            <button type="button" className="btn btn-primary small" onClick={send} disabled={!loc || !label}>
              {loc ? s.send : s.noLoc}
            </button>
          )}
        </section>
      )}
    </>
  );
}

function RatTab({ s, loc, onSent, fail }: { s: S; loc: Loc | null; onSent: () => void; fail: (e: unknown) => void }) {
  const [sev, setSev] = useState<"ringan" | "sedang" | "berat">("sedang");
  const [note, setNote] = useState("");
  const [sent, setSent] = useState(false);
  const send = async () => {
    if (!loc) return;
    try {
      await api.sigapReport({
        lat: loc.lat,
        lon: loc.lon,
        label: "tikus",
        source: "laporan_cepat",
        severity: sev,
        needs_review: true,
        note: note || null,
        block_id: loc.block?.id ?? null,
        block_name: loc.block?.name ?? null,
      });
      setSent(true);
      setNote("");
      onSent();
    } catch (e) {
      fail(e);
    }
  };
  return (
    <section className="felt pad sg-result">
      <p className="small muted">{s.ratWhy}</p>
      <p className="tiny muted">{s.severity}</p>
      <div className="seg sg-part" role="radiogroup">
        {(["ringan", "sedang", "berat"] as const).map((k) => (
          <button key={k} type="button" role="radio" aria-checked={sev === k} className={sev === k ? "on" : ""} onClick={() => (setSev(k), setSent(false))}>
            {s.sev[k]}
          </button>
        ))}
      </div>
      <label className="sg-field">
        <span className="tiny muted">{s.note}</span>
        <input value={note} maxLength={400} onChange={(e) => setNote(e.target.value)} />
      </label>
      {sent ? (
        <p className="small ok-flag sg-flag">{s.sent}</p>
      ) : (
        <button type="button" className="btn btn-primary small" onClick={send} disabled={!loc}>
          {loc ? s.send : s.noLoc}
        </button>
      )}
    </section>
  );
}

function PplTab({
  s,
  reports,
  name,
  status,
  onDone,
  fail,
}: {
  s: S;
  reports: SigapReport[];
  name: (k: string) => string;
  status: SigapStatus | null;
  onDone: () => void;
  fail: (e: unknown) => void;
}) {
  const { lang } = useLang();
  const [pin, setPin] = useState("");
  const [who, setWho] = useState("PPL");
  const [labels, setLabels] = useState<Record<string, string>>({});
  const pending = reports.filter((r) => r.status === "pending");
  const done = reports.filter((r) => r.status !== "pending").slice(0, 12);

  const act = async (r: SigapReport, st: "verified" | "rejected") => {
    try {
      await api.sigapReview(r.id, { status: st, label: labels[r.id] || undefined, reviewer: who, pin: pin || undefined });
      onDone();
    } catch (e) {
      fail(e);
    }
  };
  const when = (iso: string) => new Date(iso).toLocaleString(lang === "id" ? "id-ID" : "en-GB", { dateStyle: "medium", timeStyle: "short" });

  return (
    <>
      <div className="sg-where-row">
        <label className="sg-field">
          <span className="tiny muted">{s.reviewer}</span>
          <input value={who} maxLength={60} onChange={(e) => setWho(e.target.value)} />
        </label>
        <label className="sg-field">
          <span className="tiny muted">{s.pin}</span>
          <input type="password" value={pin} onChange={(e) => setPin(e.target.value)} inputMode="numeric" />
        </label>
      </div>
      <h3 className="sg-h">{s.pending}</h3>
      {pending.length === 0 && <p className="small muted">{s.none}</p>}
      <ol className="off-list">
        {pending.map((r) => (
          <li key={r.id} className="felt off-row sg-rep" style={{ ["--st" as string]: "#e2a93b" }}>
            {r.photo && <img src={`/api/sigap/reports/${r.id}/photo`} alt="" loading="lazy" />}
            <div>
              <p className="off-head-line">
                {name(r.label)}
                {r.count != null && r.label === "wereng" ? ` · ${r.count}` : ""}
                {r.severity ? ` · ${s.sev[r.severity]}` : ""}
              </p>
              <p className="tiny muted tabular">
                {when(r.created_at)} · {r.block_name ?? `${r.lat.toFixed(4)}, ${r.lon.toFixed(4)}`}
                {r.confidence != null ? ` · ${Math.round(r.confidence * 100)}%` : ""}
                {r.needs_review ? ` · ${s.review}` : ""}
              </p>
              {r.note && <p className="small">{r.note}</p>}
              <div className="off-actions">
                <select value={labels[r.id] ?? r.label} onChange={(e) => setLabels((l) => ({ ...l, [r.id]: e.target.value }))}>
                  {status &&
                    Object.values(status.classes).map((c) => (
                      <option key={c.key} value={c.key}>
                        {c.name[lang]}
                      </option>
                    ))}
                </select>
                <button type="button" className="btn btn-primary small" onClick={() => act(r, "verified")}>
                  {s.verify}
                </button>
                <button type="button" className="btn btn-ghost small" onClick={() => act(r, "rejected")}>
                  {s.reject}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ol>
      {done.length > 0 && (
        <>
          <h3 className="sg-h">{s.recent}</h3>
          <ul className="sg-done">
            {done.map((r) => (
              <li key={r.id} className="small">
                <span className={`sg-dot ${r.status}`} /> {name(r.label)} · {s.status[r.status]} · <span className="muted tiny">{when(r.created_at)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

const DOT: Record<string, string> = { penyakit: "#7a5bc4", hama: "#c4571e", sehat: "#4f8a3a" };

function ReportMap({
  reports,
  blocks,
  warnings,
  loc,
  onPick,
  name,
  legend,
}: {
  reports: SigapReport[];
  blocks: WatchField[];
  warnings: SigapWarnings | null;
  loc: Loc | null;
  onPick: (lat: number, lon: number) => void;
  name: (k: string) => string;
  legend: string[];
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);
  const [ready, setReady] = useState(false);
  const pick = useRef(onPick);
  pick.current = onPick;

  useEffect(() => {
    if (!el.current) return;
    const m = new maplibregl.Map({ container: el.current, style: STYLE, center: [105.3356, -5.0998], zoom: 14, attributionControl: { compact: true } });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    m.on("load", () => {
      m.addSource("blocks", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "b-fill", type: "fill", source: "blocks", paint: { "fill-color": ["case", ["get", "warn"], "#c4571e", "#ffffff"], "fill-opacity": ["case", ["get", "warn"], 0.35, 0.08] } });
      m.addLayer({ id: "b-line", type: "line", source: "blocks", paint: { "line-color": ["case", ["get", "warn"], "#c4571e", "#ffffff"], "line-width": 2 } });
      m.addSource("reports", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({
        id: "r-dot",
        type: "circle",
        source: "reports",
        paint: {
          "circle-radius": 8,
          "circle-color": ["get", "color"],
          "circle-opacity": ["case", ["get", "verified"], 1, 0.15],
          "circle-stroke-color": ["get", "color"],
          "circle-stroke-width": 2.5,
        },
      });
      m.addLayer({
        id: "r-label",
        type: "symbol",
        source: "reports",
        layout: { "text-field": ["get", "name"], "text-size": 11, "text-offset": [0, 1.4], "text-font": ["Open Sans Semibold"] },
        paint: { "text-color": "#ffffff", "text-halo-color": "#1b2a23", "text-halo-width": 1.3 },
      });
      m.on("click", (e) => pick.current(e.lngLat.lat, e.lngLat.lng));
      setReady(true);
    });
    map.current = m;
    return () => m.remove();
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    (m.getSource("blocks") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: blocks.map((b) => ({ type: "Feature" as const, properties: { warn: !!warnings?.blocks[b.id]?.warning }, geometry: b.geometry })),
    });
    const shown = reports.filter((r) => r.status !== "rejected");
    (m.getSource("reports") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: shown.map((r) => ({
        type: "Feature" as const,
        properties: { color: DOT[r.kind] ?? DOT.hama, verified: r.status === "verified", name: name(r.label) },
        geometry: { type: "Point" as const, coordinates: [r.lon, r.lat] },
      })),
    });
    const pts: [number, number][] = [...shown.map((r) => [r.lon, r.lat] as [number, number]), ...blocks.flatMap((b) => b.geometry.coordinates[0] as [number, number][])];
    if (pts.length && !m.getBounds().contains(pts[0])) {
      const bb = new maplibregl.LngLatBounds();
      pts.forEach((p) => bb.extend(p));
      m.fitBounds(bb, { padding: 60, maxZoom: 16, duration: 600 });
    }
  }, [reports, blocks, warnings, ready, name]);

  useEffect(() => {
    const m = map.current;
    if (!m || !ready) return;
    marker.current?.remove();
    if (loc) {
      marker.current = new maplibregl.Marker({ color: "#1c868b" }).setLngLat([loc.lon, loc.lat]).addTo(m);
      m.easeTo({ center: [loc.lon, loc.lat], duration: 500 });
    }
  }, [loc, ready]);

  return (
    <>
      <div ref={el} className="field-map" role="application" aria-label="Peta sebaran laporan / report map" />
      <div className="sg-legend felt">
        <span>
          <i className="sg-dot verified" /> {legend[0]}
        </span>
        <span>
          <i className="sg-dot pending" /> {legend[1]}
        </span>
      </div>
    </>
  );
}
