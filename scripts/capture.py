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
        for name, w, h in [("desktop", 1440, 900), ("mobile", 390, 844)]:
            pg = browser.new_page(viewport={"width": w, "height": h})
            pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
            pg.goto(base + "/app", wait_until="networkidle")
            time.sleep(3)
            pg.screenshot(path=str(out / f"app-{name}-empty.png"))
            pg.get_by_role("button", name="Pakai lahan contoh").first.click()
            pg.wait_for_selector(".tabs", timeout=240000)
            time.sleep(3)
            pg.screenshot(path=str(out / f"app-{name}-summary.png"))
            for tab in ["Kering", "Banjir", "Hama", "Air"]:
                pg.get_by_role("tab", name=tab).click()
                time.sleep(1.2)
                if name == "mobile":
                    pg.locator(".drawer").evaluate("e => e.scrollIntoView()")
                pg.screenshot(path=str(out / f"app-{name}-{tab.lower()}.png"))
            pg.get_by_role("button", name="Tanya Si Padi").click()
            pg.get_by_role("button", name="Apakah sawah saya akan kekeringan?").click()
            time.sleep(4)
            pg.screenshot(path=str(out / f"app-{name}-chat.png"))
            pg.close()
    browser.close()
    print("console errors:", errors[:10])
