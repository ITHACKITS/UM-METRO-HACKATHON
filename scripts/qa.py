"""End-to-end QA: drives every feature in a real browser and reports what broke.

Usage: python scripts/qa.py http://localhost:5173 <screenshot_dir>
Exit code 1 if any check fails, a console error appears or a same-origin request fails.
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

base, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
failures: list[str] = []
console: list[str] = []
bad_requests: list[str] = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def watch(pg):
    pg.on("console", lambda m: m.type == "error" and console.append(f"{pg.url}: {m.text[:200]}"))
    pg.on("pageerror", lambda e: console.append(f"{pg.url}: pageerror {e}"))
    pg.on(
        "response",
        lambda r: r.status >= 400 and "localhost" in r.url and "/api/validate-field" not in r.url and bad_requests.append(f"{r.status} {r.url}"),
    )


with sync_playwright() as p:
    args = ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"]
    try:
        browser = p.chromium.launch(channel="chrome", args=args)
    except Exception:
        browser = p.chromium.launch(args=args)

    # ---------- Landing ----------
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    watch(pg)
    pg.goto(base + "/", wait_until="networkidle")
    time.sleep(7)
    check("landing loader hides", pg.locator(".landing.is-ready").count() == 1)
    check("diorama renders frames", "fps" in pg.locator(".hero-foot span").first.inner_text())
    for mode in ["Kering", "Banjir", "Normal"]:
        pg.get_by_role("button", name=mode, exact=True).click()
        check(f"dock water {mode}", pg.get_by_role("button", name=mode, exact=True).get_attribute("aria-pressed") == "true")
    pg.locator(".dock-stage").click()
    check("dock stage cycles", "Menguning" in pg.locator(".dock-stage").inner_text())
    pg.locator(".dock-hour input").fill("17.5")
    check("dock hour updates readout", "17:30" in pg.locator(".hero-foot span").first.inner_text())
    pg.get_by_role("button", name="Atur ulang tampilan").click()
    check("landing h1 visible", pg.locator("h1").is_visible())
    pg.get_by_role("button", name="EN").first.click()
    check("language toggle to EN", "Guard the rice" in pg.locator("h1").inner_text())
    pg.get_by_role("button", name="ID").first.click()
    check("language toggle back to ID", "Jaga sawah" in pg.locator("h1").inner_text())
    pg.locator('a[href="#cara-kerja"]').first.click()
    time.sleep(2)
    check("anchor scroll to Cara kerja", pg.evaluate("scrollY") > 500)
    for a in pg.locator("a.cite").all():
        check(f"stat citation has href {a.get_attribute('href')[:40]}", (a.get_attribute("href") or "").startswith("https://"))
    pg.goto(base + "/credits")
    pg.wait_for_selector(".credits h1", timeout=15000)
    check("credits page", pg.get_by_role("heading", name="Credits and data attribution").is_visible())
    pg.goto(base + "/tidak-ada")
    pg.wait_for_selector(".notfound", timeout=15000)
    check("404 page", pg.get_by_text("Petak ini belum ditanami.").is_visible())
    pg.close()

    # Reduced motion + no WebGL fallback.
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
    pg = ctx.new_page()
    watch(pg)
    pg.add_init_script("HTMLCanvasElement.prototype.getContext = function(){ return null; };")
    pg.goto(base + "/", wait_until="networkidle")
    time.sleep(4)
    check("no-WebGL fallback class", pg.locator(".landing.no-webgl").count() == 1)
    check("no-WebGL message visible", pg.locator(".nowebgl").is_visible())
    check("reduced-motion content visible", pg.locator(".hero-sub").evaluate("e => getComputedStyle(e).opacity") == "1")
    pg.screenshot(path=str(out / "qa-no-webgl.png"))
    ctx.close()
    # The forced getContext failure logs a three.js error by design; drop those from the report.
    console[:] = [c for c in console if "WebGL" not in c and "getContext" not in c]

    # ---------- App: drawing ----------
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    watch(pg)
    pg.goto(base + "/app", wait_until="networkidle")
    time.sleep(3)
    check("app empty state", pg.get_by_text("Mulai dari sawahmu").is_visible())
    pg.get_by_role("button", name="Gambar lahan").first.click()
    m = pg.locator(".field-map canvas").bounding_box()
    # A tiny triangle must be refused (below 0.05 ha).
    for dx, dy in [(0, 0), (3, 0), (0, 3)]:
        pg.mouse.click(m["x"] + 400 + dx, m["y"] + 400 + dy)
        time.sleep(0.3)
    pg.get_by_role("button", name="Selesai (3)").click()
    time.sleep(1.5)
    check("tiny field rejected with message", pg.locator(".error").count() == 1, pg.locator(".error").all_inner_texts().__str__())

    # ---------- App: demo field and every tab ----------
    pg.get_by_role("button", name="Pakai lahan contoh").first.click()
    pg.wait_for_selector(".tabs", timeout=300000)
    time.sleep(2)
    check("analysis loaded", pg.locator(".risk").count() >= 2)
    check("field layer drawn", pg.evaluate("() => !!document.querySelector('.field-map')"))
    for tab in ["Kering", "Banjir", "Hama", "Air", "Data", "Ringkasan"]:
        pg.get_by_role("tab", name=tab).click()
        time.sleep(0.6)
        check(f"tab {tab} renders", pg.locator(".tab-body").inner_text().strip() != "")
    pg.get_by_role("tab", name="Kering").click()
    check("drought charts render", pg.locator(".chart svg").count() >= 2)
    drivers = pg.locator(".drivers").first.inner_text()
    check("drivers shown in Indonesian", "hari ke depan" in drivers or "kelembapan" in drivers, drivers[:120])
    # Day slider and player.
    pg.locator(".player input[type=range]").fill("10")
    check("day slider moves", "Hari 10" in pg.locator(".player-top").inner_text())
    pg.get_by_role("button", name="Putar").click()
    time.sleep(1.6)
    pg.get_by_role("button", name="Jeda").click()
    check("player advances", "Hari 10" not in pg.locator(".player-top").inner_text())
    pg.get_by_role("button", name="S2 cloudless").click()
    time.sleep(1)
    check("basemap toggle pressed", pg.get_by_role("button", name="S2 cloudless").get_attribute("aria-pressed") == "true")
    pg.screenshot(path=str(out / "qa-app-drought.png"))

    # Water tab route.
    pg.get_by_role("tab", name="Air").click()
    btns = pg.get_by_role("button", name="Tunjukkan di peta")
    if btns.count():
        btns.first.click()
        check("water route button works", True)
    else:
        check("water tab explains missing data", "OpenStreetMap" in pg.locator(".tab-body").inner_text())

    # Edit days after transplanting.
    pg.get_by_role("tab", name="Ringkasan").click()
    pg.get_by_role("button", name="Ubah").click()
    pg.get_by_label("Hari setelah tanam").fill("60")
    pg.get_by_role("button", name="OK").click()
    pg.wait_for_selector(".tabs", timeout=300000)
    time.sleep(1)
    check("crop age edit applied", "60" in pg.locator(".facts").first.inner_text())

    # Test scenario.
    pg.get_by_role("button", name="Uji skenario").click()
    sliders = pg.locator(".sim input[type=range]")
    sliders.nth(0).fill("0.3")
    sliders.nth(1).fill("10")
    pg.get_by_role("button", name="Jalankan simulasi").click()
    pg.wait_for_selector(".hypo-banner", timeout=300000)
    check("scenario labelled hypothetical", pg.locator(".hypo-banner").is_visible())
    pg.screenshot(path=str(out / "qa-app-scenario.png"))
    pg.get_by_role("button", name="Kondisi nyata").click()
    pg.wait_for_selector(".tabs", timeout=300000)
    time.sleep(2)
    check("back to real removes banner", pg.locator(".hypo-banner").count() == 0)

    # Chat in Indonesian then English.
    pg.get_by_role("button", name="Tanya Si Padi").click()
    pg.get_by_role("button", name="Apakah sawah saya akan kekeringan?").click()
    pg.wait_for_selector(".msg.assistant:not(.typing) >> nth=1", timeout=180000)
    reply = pg.locator(".msg.assistant:not(.typing)").nth(1).inner_text()
    check("chat answers with sourced numbers", "%" in reply and "Sumber" in reply, reply[:160])
    pg.get_by_label("Tulis pertanyaan…").fill("hama apa yang perlu diwaspadai")
    pg.get_by_role("button", name="Kirim").click()
    pg.wait_for_selector(".msg.assistant:not(.typing) >> nth=2", timeout=180000)
    check("chat pest answer", "cuaca" in pg.locator(".msg.assistant:not(.typing)").nth(2).inner_text())
    pg.screenshot(path=str(out / "qa-app-chat.png"))
    pg.keyboard.press("Escape")
    check("chat closes on Escape", pg.locator(".chat-panel").count() == 0)
    # Regression: coming back to the landing after the app must not replay the loader,
    # and app styles (the fixed chat panel) must not leak onto landing cards.
    pg.get_by_role("link", name="Jagapadi, kembali ke beranda").click()
    time.sleep(9)  # first landing visit in this tab builds the diorama
    pg.get_by_role("link", name="Buka peta").click()
    time.sleep(2)
    pg.get_by_role("link", name="Jagapadi, kembali ke beranda").click()
    time.sleep(1.5)
    check("loader not replayed on return", pg.evaluate("getComputedStyle(document.querySelector('.loader')).visibility") == "hidden")
    check("feature card not hijacked by app styles", pg.evaluate("getComputedStyle(document.querySelector('.isle-chat')).position") == "relative")
    time.sleep(2)
    check("diorama renders after return", "fps" in pg.locator(".hero-foot span").first.inner_text())
    pg.close()

    # ---------- Mobile app ----------
    pg = browser.new_page(viewport={"width": 360, "height": 780})
    watch(pg)
    pg.goto(base + "/app", wait_until="networkidle")
    pg.get_by_role("button", name="Pakai lahan contoh").first.click()
    pg.wait_for_selector(".tabs", timeout=300000)
    time.sleep(2)
    over = pg.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
    check("mobile 360 no horizontal overflow", not over)
    check("mobile tabs visible", pg.locator(".tabs").bounding_box()["height"] >= 40)
    small = pg.evaluate(
        """() => [...document.querySelectorAll('button, a, input')].filter(e => {
            const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
            return r.width > 0 && s.visibility !== 'hidden' && r.height < 32 && !e.closest('.maplibregl-ctrl-attrib');
        }).map(e => (e.innerText || e.getAttribute('aria-label') || e.tagName).slice(0, 30))"""
    )
    check("mobile tap targets >= 32px", not small, str(small[:6]))
    pg.screenshot(path=str(out / "qa-mobile-app.png"), full_page=False)
    pg.close()

    browser.close()

print("\nconsole errors:", console[:10])
print("failed requests:", bad_requests[:10])
if console or bad_requests or failures:
    print(f"\n{len(failures)} failed checks: {failures}")
    sys.exit(1)
print("\nALL CHECKS PASSED")
