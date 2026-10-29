"""Capture landing scroll positions and app states for review and docs/screenshots.

Usage: python scripts/capture.py <base_url> <out_dir> [landing|app|all]
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

base, out = sys.argv[1], Path(sys.argv[2])
which = sys.argv[3] if len(sys.argv) > 3 else "all"
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="chrome", args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    except Exception:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    errors = []
    if which in ("landing", "all"):
        for name, w, h in [("desktop", 1440, 900), ("mobile", 390, 844)]:
            pg = browser.new_page(viewport={"width": w, "height": h})
            pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
            pg.goto(base + "/", wait_until="networkidle")
            time.sleep(6)
            total = pg.evaluate("document.documentElement.scrollHeight - innerHeight")
            for i, frac in enumerate([0, 0.18, 0.38, 0.58, 0.8, 1.0]):
                pg.evaluate(f"window.scrollTo(0, {int(total * frac)})")
                time.sleep(3.2)
                pg.screenshot(path=str(out / f"landing-{name}-{i}.png"))
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
    browser.close()
    print("console errors:", errors[:10])
