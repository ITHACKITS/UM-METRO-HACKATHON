import { useState } from "react";
import { api, API_DOWN, tr, type Analysis, type Polygon, type Status } from "../lib/api";
import { useLang } from "../lib/i18n";
import { IslandGlyph } from "../components/Glyphs";

const T = {
  id: {
    status: { aman: "Aman", waspada: "Waspada", bahaya: "Bahaya" } as Record<Status, string>,
    todayT: "Hari ini, lakukan:",
    dry: "Peluang kering",
    wet: "Peluang terendam",
    weeks: "2 minggu ke depan",
    details: "Lihat detail lengkap",
    alert: "Kirim peringatan ke Telegram",
    alertBusy: "Menyiapkan…",
    alertOpen: "Buka Telegram dan tekan Mulai (Start). Pesan pertama datang dalam satu menit.",
    alertLink: "Kalau Telegram tidak terbuka, pakai tautan ini",
    alertOff: "Peringatan Telegram belum diaktifkan di server ini.",
    apiDown: "Server TUAI tidak menjawab. Coba lagi sebentar.",
    sure: {
      low: "Keyakinan rendah: data satelit lama atau tahap tanam belum pasti.",
      medium: "Keyakinan sedang.",
      high: "Keyakinan tinggi.",
    },
    stageUnsure: "Umur tanaman belum pasti. Isi hari setelah tanam di detail supaya hasilnya lebih tepat.",
  },
  en: {
    status: { aman: "Safe", waspada: "Watch", bahaya: "Danger" } as Record<Status, string>,
    todayT: "Today, do this:",
    dry: "Drought chance",
    wet: "Flooding chance",
    weeks: "next 2 weeks",
    details: "See full details",
    alert: "Send alerts to Telegram",
    alertBusy: "Preparing…",
    alertOpen: "Open Telegram and press Start. The first message arrives within a minute.",
    alertLink: "If Telegram did not open, use this link",
    alertOff: "Telegram alerts are not enabled on this server.",
    apiDown: "The TUAI server is not responding. Try again shortly.",
    sure: {
      low: "Low confidence: old satellite data or unsure crop stage.",
      medium: "Medium confidence.",
      high: "High confidence.",
    },
    stageUnsure: "The crop age is uncertain. Enter days after transplanting in the details for a better result.",
  },
};

/** The farmer view: one status, one reason, one thing to do today. */
export function SimpleView({
  a,
  field,
  name,
  dat,
  telegram,
  onDetails,
}: {
  a: Analysis;
  field: Polygon;
  name: string;
  dat: number | null;
  telegram: boolean;
  onDetails: () => void;
}) {
  const { lang } = useLang();
  const s = T[lang];
  const v = a.verdict;
  const kind = v.threat ?? "ok";
  return (
    <div className="simple">
      <section className={`verdict felt st-${v.status}`} aria-live="polite">
        <div className="verdict-top">
          <span className="verdict-badge">
            <span className="dot" aria-hidden="true" />
            {s.status[v.status]}
          </span>
          {kind !== "ok" && <IslandGlyph kind={kind} />}
        </div>
        <h2>{v.headline[lang]}</h2>
        <p className="verdict-why">{v.why[lang]}</p>
      </section>

      <section className="today felt">
        <p className="today-t">{s.todayT}</p>
        <p className="today-x">{v.today[lang]}</p>
      </section>

      <div className="odds">
        <p>
          <span>{s.dry}</span>
          <b style={{ color: "hsl(var(--drought))" }}>{Math.round(a.drought.risk.probability * 100)}%</b>
        </p>
        <p>
          <span>{s.wet}</span>
          <b style={{ color: "hsl(var(--flood))" }}>{Math.round(a.flood.risk.probability * 100)}%</b>
        </p>
        <p className="odds-note">{s.weeks}</p>
      </div>

      <p className="muted small">
        {s.sure[v.confidence]} {!a.crop.reliable && dat === null ? s.stageUnsure : ""}
      </p>

      <div className="simple-ctas">
        {telegram && <AlertButton field={field} name={name} dat={dat} />}
        <button type="button" className="btn btn-ghost" onClick={onDetails}>
          {s.details}
        </button>
      </div>
      <p className="disclaimer">{tr(a.disclaimer, lang)}</p>
    </div>
  );
}

export function AlertButton({ field, name, dat }: { field: Polygon; name: string; dat: number | null }) {
  const { lang } = useLang();
  const s = T[lang];
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const go = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.alertSubscribe(field, name, lang, dat);
      if (!r.enabled || !r.link) {
        setMsg(s.alertOff);
        return;
      }
      setLink(r.link);
      window.open(r.link, "_blank", "noopener");
    } catch (e) {
      setMsg((e as Error).message === API_DOWN ? s.apiDown : (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="alert-box">
      <button type="button" className="btn btn-primary tg" onClick={go} disabled={busy}>
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M21.5 3.6 2.9 10.8c-1.3.5-1.2 1.3-.2 1.6l4.8 1.5 1.8 5.6c.2.7.6.8 1.1.4l2.7-2.2 5 3.7c.9.5 1.5.2 1.8-.8l3.2-15.2c.3-1.4-.5-2-1.6-1.8ZM9.6 14.4l8.7-7.8c.4-.3-.1-.5-.6-.2L7.6 13.3"
          />
        </svg>
        {busy ? s.alertBusy : s.alert}
      </button>
      {link && (
        <p className="small">
          {s.alertOpen}{" "}
          <a href={link} target="_blank" rel="noopener noreferrer">
            {s.alertLink}
          </a>
          .
        </p>
      )}
      {msg && <p className="small error-inline">{msg}</p>}
    </div>
  );
}
