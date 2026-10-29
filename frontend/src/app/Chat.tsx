import { useEffect, useRef, useState } from "react";
import { api, type Polygon } from "../lib/api";
import { useLang } from "../lib/i18n";

type Msg = { role: "user" | "assistant"; content: string; note?: string };

const T = {
  id: {
    open: "Tanya Si Padi",
    title: "Si Padi",
    sub: "Menjawab dari data lahanmu",
    placeholder: "Tulis pertanyaan…",
    send: "Kirim",
    close: "Tutup",
    expand: "Layar penuh",
    voice: "Bicara",
    hello: "Halo, aku Si Padi. Tanya apa saja tentang sawah yang sudah kamu gambar. Aku hanya menjawab dari data yang ada, dan bilang kalau datanya tidak tersedia.",
    chips: ["Apakah sawah saya akan kekeringan?", "Bagaimana risiko banjirnya?", "Hama apa yang perlu diwaspadai?", "Di mana sumber air terdekat?"],
    template: "Jawaban dari templat (tanpa model bahasa)",
    error: "Maaf, Si Padi tidak bisa menjawab sekarang.",
  },
  en: {
    open: "Ask Padi",
    title: "Padi",
    sub: "Answers from your field data",
    placeholder: "Type a question…",
    send: "Send",
    close: "Close",
    expand: "Full screen",
    voice: "Speak",
    hello: "Hi, I'm Padi. Ask anything about the field you drew. I only answer from the data we have, and I'll tell you when something is unavailable.",
    chips: ["Will my field run dry?", "What is the flood risk?", "Which pests should I watch?", "Where is the nearest water?"],
    template: "Template answer (no language model)",
    error: "Sorry, Padi can't answer right now.",
  },
};

type SpeechRec = { lang: string; onresult: (e: { results: { 0: { transcript: string } }[] }) => void; start: () => void };

export function Chat({ field, dat }: { field: Polygon; dat: number | null }) {
  const { lang } = useLang();
  const t = T[lang];
  const [open, setOpen] = useState(false);
  const [full, setFull] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const list = useRef<HTMLDivElement>(null);
  const Rec = (window as unknown as { SpeechRecognition?: new () => SpeechRec; webkitSpeechRecognition?: new () => SpeechRec }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: new () => SpeechRec }).webkitSpeechRecognition;

  useEffect(() => {
    list.current?.scrollTo({ top: list.current.scrollHeight, behavior: "smooth" });
  }, [msgs, busy]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    const next: Msg[] = [...msgs, { role: "user", content: q }];
    setMsgs(next);
    setInput("");
    setBusy(true);
    try {
      const r = await api.chat(field, next.map(({ role, content }) => ({ role, content })), lang, dat);
      setMsgs([...next, { role: "assistant", content: r.text, note: r.engine === "template" ? t.template : r.note }]);
    } catch {
      setMsgs([...next, { role: "assistant", content: t.error }]);
    } finally {
      setBusy(false);
    }
  };

  const listen = () => {
    if (!Rec) return;
    const r = new Rec();
    r.lang = lang === "id" ? "id-ID" : "en-US";
    r.onresult = (e) => setInput(e.results[0][0].transcript);
    r.start();
  };

  if (!open)
    return (
      <button type="button" className="chat-fab" onClick={() => setOpen(true)} aria-label={t.open}>
        <span className="mascot-pop fab-pop">
          <img src="/mascot/si-padi-pop-128.png" srcSet="/mascot/si-padi-pop-256.png 2x" alt="" />
        </span>
        <span>{t.open}</span>
      </button>
    );

  return (
    <section className={`chat-panel felt ${full ? "full" : ""}`} aria-label={t.title} role="dialog">
      <header className="chat-head">
        <span className="mascot-pop head-pop">
          <img src="/mascot/si-padi-pop-128.png" srcSet="/mascot/si-padi-pop-256.png 2x" alt="" />
        </span>
        <div>
          <h2>{t.title}</h2>
          <p>{t.sub}</p>
        </div>
        <button type="button" className="icon-btn" onClick={() => setFull((f) => !f)} aria-label={t.expand} aria-pressed={full}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M3 7V3h4M15 7V3h-4M3 11v4h4M15 11v4h-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
        <button type="button" className="icon-btn" onClick={() => setOpen(false)} aria-label={t.close}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M4 4l10 10M14 4L4 14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
      </header>
      <div className="chat-list" ref={list} aria-live="polite">
        <div className="msg assistant">{t.hello}</div>
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
            {m.note && <small>{m.note}</small>}
          </div>
        ))}
        {busy && (
          <div className="msg assistant typing" aria-label="…">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>
      {msgs.length === 0 && (
        <div className="chips">
          {t.chips.map((c) => (
            <button type="button" key={c} onClick={() => send(c)}>
              {c}
            </button>
          ))}
        </div>
      )}
      <form
        className="chat-form"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={t.placeholder} aria-label={t.placeholder} maxLength={500} />
        {Rec && (
          <button type="button" className="icon-btn" onClick={listen} aria-label={t.voice}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <rect x="6" y="2" width="6" height="9" rx="3" stroke="currentColor" strokeWidth="1.8" />
              <path d="M3.5 8.5a5.5 5.5 0 0 0 11 0M9 14v2.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        )}
        <button type="submit" className="btn btn-primary small" disabled={busy || !input.trim()}>
          {t.send}
        </button>
      </form>
    </section>
  );
}
