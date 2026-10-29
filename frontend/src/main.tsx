import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { LangProvider } from "./lib/i18n";
import { PaddyLoader } from "./components/PaddyLoader";
import "./styles/tokens.css";
import "./styles/global.css";

const Landing = lazy(() => import("./landing/Landing"));
const Workspace = lazy(() => import("./app/Workspace"));
const Officer = lazy(() => import("./app/Officer"));
const Credits = lazy(() => import("./components/Credits"));

function NotFound() {
  return (
    <main className="notfound">
      <img src="/mascot/mascot-laptop-256.png" srcSet="/mascot/mascot-laptop-256@2x.png 2x" width={220} height={220} alt="" />
      <h1>Petak ini belum ditanami.</h1>
      <p>Halaman yang kamu cari tidak ada.</p>
      <Link to="/" className="btn btn-primary">
        Kembali ke beranda
      </Link>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LangProvider>
      <BrowserRouter>
        <Suspense
          fallback={
            <div className="boot" role="status" aria-label="Memuat">
              <PaddyLoader size={120} />
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/app" element={<Workspace />} />
            <Route path="/ppl" element={<Officer />} />
            <Route path="/credits" element={<Credits />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </LangProvider>
  </StrictMode>,
);
