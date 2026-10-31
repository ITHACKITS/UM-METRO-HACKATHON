"""Capture landing scroll positions and app states for review and docs/screenshots.

Usage: python scripts/capture.py <base_url> <out_dir> [landing|app|tuai|all]

`landing` and `app` write the file names README uses, so `capture.py <url> docs/screenshots all`
refreshes every README image. `tuai` adds Sigap, Lancar and Taksir; it sends one Sigap report
with the public-domain leaf photo in scripts/fixtures and rejects it again afterwards.
"""
import sys
import time
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "daun-blas.jpg"

from playwright.sync_api import sync_playwright

base, out = sys.argv[1], Path(sys.argv[2])
which = sys.argv[3] if len(sys.argv) > 3 else "all"
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome", args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
    except Exception:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    errors = []
    if which in ("landing", "all"):
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        pg.goto(base + "/", wait_until="networkidle")
        time.sleep(7)
        pg.screenshot(path=str(out / "landing-hero.png"))
        # The features chapter is framed on its five cards, the others on their opening card.
        for i, sel in enumerate(["#masalah", "#cara-kerja", "#fitur .island-grid", "#data"], start=2):
            block = "center" if "grid" in sel else "start"
            pg.evaluate(f"document.querySelector('{sel}').scrollIntoView({{block: '{block}'}})")
            time.sleep(4)
            pg.screenshot(path=str(out / f"story-0{i}.png"))
        pg.close()
        pg = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        pg.goto(base + "/", wait_until="networkidle")
        time.sleep(7)
        pg.screenshot(path=str(out / "mobile-landing.png"))
        pg.close()
    if which in ("app", "all"):
        # File names match docs/screenshots, so `capture.py <url> docs/screenshots app` refreshes the README.
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        pg.goto(base + "/app", wait_until="networkidle")
        time.sleep(3)
        pg.screenshot(path=str(out / "app-empty.png"))
        pg.get_by_role("button", name="Pakai lahan contoh").first.click()
        pg.wait_for_selector(".verdict", timeout=240000)
        time.sleep(3)
        pg.screenshot(path=str(out / "app-petani.png"))
        pg.get_by_role("button", name="Ahli", exact=True).click()
        pg.wait_for_selector(".tabs")
        time.sleep(2)
        pg.screenshot(path=str(out / "app-ringkasan.png"))
        for tab, file in [("Kering", "app-kering"), ("Banjir", "app-banjir"), ("Hama", "app-hama")]:
            pg.get_by_role("tab", name=tab).click()
            time.sleep(1.2)
            pg.screenshot(path=str(out / f"{file}.png"))
        pg.get_by_role("tab", name="Kering").click()
        pg.get_by_role("button", name="Tanya Si Padi").click()
        pg.get_by_role("button", name="Apakah sawah saya akan kekeringan?").click()
        pg.wait_for_selector(".msg.assistant:not(.typing) >> nth=1", timeout=180000)
        time.sleep(1.5)
        pg.screenshot(path=str(out / "app-chat.png"))
        pg.keyboard.press("Escape")
        pg.get_by_role("button", name="Uji skenario").click()
        sliders = pg.locator(".sim input[type=range]")
        sliders.nth(0).fill("0.3")
        sliders.nth(1).fill("10")
        pg.get_by_role("button", name="Jalankan simulasi").click()
        pg.wait_for_selector(".hypo-banner", timeout=240000)
        time.sleep(2)
        pg.screenshot(path=str(out / "app-simulator.png"))
        # Officer dashboard with the sample farmer group.
        pg.goto(base + "/ppl", wait_until="networkidle")
        pg.evaluate("localStorage.clear()")
        pg.reload(wait_until="networkidle")
        pg.get_by_role("button", name="Pakai contoh kelompok tani").click()
        pg.wait_for_selector("button:has-text('Periksa semua')", timeout=600000)
        time.sleep(3)
        pg.screenshot(path=str(out / "ppl-dashboard.png"))
        pg.close()

        pg = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        pg.goto(base + "/app", wait_until="networkidle")
        pg.get_by_role("button", name="Pakai lahan contoh").first.click()
        pg.wait_for_selector(".verdict", timeout=240000)
        time.sleep(2)
        pg.locator(".verdict").evaluate("e => e.scrollIntoView({block: 'start'})")
        time.sleep(1)
        pg.screenshot(path=str(out / "mobile-app.png"))
        pg.close()
    if which in ("tuai", "all"):
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
        # TUAI Sigap: real leaf photo, location on the map, report, PPL queue.
        pg.goto(base + "/sigap", wait_until="networkidle")
        pg.locator("input[type=file]").set_input_files(str(FIXTURE))
        pg.wait_for_selector(".sg-result", timeout=300000)
        pg.locator(".field-map canvas").click(position={"x": 520, "y": 430})
        pg.get_by_role("button", name="Kirim laporan").click()
        pg.wait_for_selector("text=Terkirim", timeout=30000)
        time.sleep(1.5)
        pg.screenshot(path=str(out / "app-sigap.png"))
        pg.get_by_role("tab", name="Cek PPL").click()
        time.sleep(1.5)
        pg.screenshot(path=str(out / "app-sigap-ppl.png"))
        pg.locator(".sg-rep").first.get_by_role("button", name="Tolak").click()
        time.sleep(1)
        # TUAI Lancar and Taksir on the sample farmer group, with planting dates filled in.
        pg.goto(base + "/ppl", wait_until="networkidle")
        pg.evaluate("localStorage.clear()")
        pg.reload(wait_until="networkidle")
        pg.get_by_role("button", name="Pakai contoh kelompok tani").click()
        pg.wait_for_selector("button:has-text('Periksa semua')", timeout=600000)
        pg.evaluate(
            """() => {
              const dates = ['2026-08-25', '2026-09-05', '2026-08-20', '2026-09-20', '2026-10-05'];
              const l = JSON.parse(localStorage.getItem('jagapadi-watchlist'));
              l.forEach((f, i) => Object.assign(f, { planting_date: dates[i % 5], variety: 'ciherang' }));
              localStorage.setItem('jagapadi-watchlist', JSON.stringify(l));
            }"""
        )
        pg.reload(wait_until="networkidle")
        pg.get_by_role("tab", name="Giliran air").click()
        pg.get_by_role("button", name="Hitung urutan giliran air").click()
        pg.wait_for_selector(".lc-rank", timeout=600000)
        time.sleep(2)
        pg.screenshot(path=str(out / "app-lancar.png"))
        pg.get_by_role("tab", name="Taksir panen").click()
        pg.get_by_role("button", name="Taksir panen").click()
        pg.wait_for_selector(".off-list .off-badge", timeout=600000)
        time.sleep(2)
        pg.screenshot(path=str(out / "app-taksir.png"))
        # Printed field report as PDF.
        pg.goto(base + "/app", wait_until="networkidle")
        pg.get_by_role("button", name="Pakai lahan contoh").first.click()
        pg.wait_for_selector(".verdict", timeout=240000)
        time.sleep(2)
        pg.emulate_media(media="print")
        time.sleep(1)
        try:
            pg.pdf(path=str(out / "laporan-contoh.pdf"), format="A4", print_background=True)
        except Exception as e:  # headed Chrome cannot print to PDF
            print("pdf skipped:", e)
        pg.close()
    browser.close()
    print("console errors:", errors[:10])
