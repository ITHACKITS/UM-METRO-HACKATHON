"""Build the TUAI logo set from code.

The mark: a rice stalk with a drooping golden panicle and two leaves, growing out of
paddy water, on a teal felt badge with a stitched edge. The wordmark is Instrument Serif
Italic (OFL) converted to outlines, so the SVGs look the same without the web font.

Usage: python scripts/brand_assets.py [path/to/InstrumentSerif-Italic.ttf]
Without a path the font is downloaded from the google/fonts repository.
Writes to frontend/public/ and frontend/public/logo/, and renders PNGs with Playwright.
"""

import base64
import math
import sys
import tempfile
import urllib.request
from io import BytesIO
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "frontend" / "public"
LOGO = PUBLIC / "logo"
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/instrumentserif/InstrumentSerif-Italic.ttf"

TEAL, CREAM, GOLD, SAGE, INK, PAPER = "#1c868b", "#f3e6c4", "#e2a93b", "#a9cf86", "#1b2a23", "#f4ead9"

# Panicle stem: cubic from the stalk tip, arching right and drooping down.
PANICLE = [(32.5, 14), (40, 8), (50, 12), (49, 31)]


def _bez(p, t):
    u = 1 - t
    return tuple(u**3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t**3 * d for a, b, c, d in zip(*p))


def _tan(p, t):
    u = 1 - t
    return tuple(3 * u * u * (b - a) + 6 * u * t * (c - b) + 3 * t * t * (d - c) for a, b, c, d in zip(*p))


def _grain(cx, cy, ang, length, width):
    return (
        f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{length / 2:.2f}" ry="{width / 2:.2f}" '
        f'transform="rotate({math.degrees(ang):.1f} {cx:.2f} {cy:.2f})"/>'
    )


def mark(bg=TEAL, fg=CREAM, gold=GOLD, leaf=SAGE, stitch=True) -> str:
    grains = []
    n = 8
    for i in range(n):
        t = 0.08 + 0.8 * i / (n - 1)
        x, y = _bez(PANICLE, t)
        dx, dy = _tan(PANICLE, t)
        a = math.atan2(dy, dx)
        side = 1 if i % 2 else -1
        length, width = 7.6 - 1.8 * i / (n - 1), 3.6 - 0.7 * i / (n - 1)
        nx, ny = -math.sin(a), math.cos(a)
        gx = x + nx * side * width * 0.45 + math.cos(a) * length * 0.3
        gy = y + ny * side * width * 0.45 + math.sin(a) * length * 0.3
        grains.append(_grain(gx, gy, a + side * 0.38, length, width))
    ex, ey = _bez(PANICLE, 1.0)
    dx, dy = _tan(PANICLE, 1.0)
    grains.append(_grain(ex, ey, math.atan2(dy, dx), 5.2, 2.8))
    (a, b), (c, d), (e, f), (g, h) = PANICLE
    parts = [f'<rect x="2" y="2" width="60" height="60" rx="17" fill="{bg}"/>']
    if stitch:
        parts.append(
            f'<rect x="6.5" y="6.5" width="51" height="51" rx="13" fill="none" stroke="{fg}" '
            'stroke-opacity=".45" stroke-width="1.2" stroke-dasharray="2.6 2.4"/>'
        )
    parts += [
        f'<path d="M12 47.5c6.5-3.2 13-3.2 20 0s13.5 3.2 20 0" fill="none" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>',
        f'<path d="M17 53c5-2.2 10-2.2 15 0s10 2.2 15 0" fill="none" stroke="{fg}" stroke-opacity=".6" stroke-width="2.2" stroke-linecap="round"/>',
        f'<path d="M29.5 45.5C22 44 16.5 37.5 16 28c7.5 2.5 12.5 9 13.5 17.5Z" fill="{leaf}"/>',
        f'<path d="M30.5 45.5c4.8-1.6 8.8-6.2 9.6-13-5 1.8-8.6 6.4-9.6 13Z" fill="{leaf}" opacity=".85"/>',
        f'<path d="M30 47C29.5 36 30 22 32.5 14" fill="none" stroke="{fg}" stroke-width="3.8" stroke-linecap="round"/>',
        f'<path d="M{a} {b}C{c} {d} {e} {f} {g} {h}" fill="none" stroke="{gold}" stroke-width="2" stroke-linecap="round"/>',
        f'<g fill="{gold}">' + "".join(grains) + "</g>",
    ]
    return "\n  ".join(parts)


def svg(body: str, w=64, h=64) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="TUAI">\n'
        f"  {body}\n</svg>\n"
    )


def wordmark_path(font_path: Path, text="tuai", size=46, x=76, baseline=50, tracking=-1.5) -> tuple[str, float]:
    font = TTFont(font_path)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    pen = SVGPathPen(gs)
    cursor = x
    for ch in text:
        name = cmap[ord(ch)]
        gs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, cursor, baseline)))
        cursor += gs[name].width * scale + tracking
    return pen.getCommands(), cursor


def lockup(word: str, ink: str, width: int) -> str:
    return svg(
        f'<g transform="translate(2 4)">\n  {mark()}\n  </g>\n  <path d="{word}" fill="{ink}"/>', width, 72
    )


def render(page, svg_text: str, size: int, transparent=True) -> Image.Image:
    page.set_viewport_size({"width": size, "height": size})
    page.set_content(
        f'<html><body style="margin:0;background:transparent">'
        f'<img src="data:image/svg+xml;base64,{base64.b64encode(svg_text.encode()).decode()}" width="{size}" height="{size}">'
        "</body></html>"
    )
    return Image.open(BytesIO(page.screenshot(omit_background=transparent)))


def main() -> None:
    if len(sys.argv) > 1:
        font_path = Path(sys.argv[1])
    else:
        font_path = Path(tempfile.gettempdir()) / "InstrumentSerif-Italic.ttf"
        if not font_path.exists():
            urllib.request.urlretrieve(FONT_URL, font_path)
    word, end = wordmark_path(font_path)
    width = int(end) + 8

    icon = svg(mark())
    small = svg(mark(stitch=False))
    files = {
        LOGO / "tuai-icon.svg": icon,
        PUBLIC / "favicon.svg": small,
        LOGO / "tuai-icon-mono-dark.svg": svg(mark(bg=INK, fg=PAPER, gold=PAPER, leaf=PAPER)),
        LOGO / "tuai-icon-mono-light.svg": svg(mark(bg=PAPER, fg=INK, gold=INK, leaf=INK)),
        LOGO / "tuai-lockup.svg": lockup(word, INK, width),
        LOGO / "tuai-lockup-dark.svg": lockup(word, CREAM, width),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for size in (192, 512):
            render(page, icon, size).save(LOGO / f"tuai-icon-{size}.png", optimize=True)
        render(page, icon, 180).save(PUBLIC / "apple-touch-icon.png", optimize=True)
        render(page, small, 256).save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

        # Link preview: lockup and tagline on cream, the waving mascot on the right.
        mascot = (PUBLIC / "mascot" / "mascot-waving-1024.png").as_uri()
        lock = (LOGO / "tuai-lockup.svg").as_uri()
        page.set_viewport_size({"width": 1200, "height": 630})
        og = Path(tempfile.gettempdir()) / "tuai-og.html"
        og.write_text(
            f"""<html><head><link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500&display=swap" rel="stylesheet"></head>
<body style="margin:0;width:1200px;height:630px;background:{PAPER};display:flex;align-items:center;justify-content:space-between;padding:0 40px 0 96px;box-sizing:border-box;font-family:Manrope,sans-serif">
<div><img src="{lock}" height="125"><p style="margin:28px 0 0 8px;font-size:34px;color:{INK};opacity:.75;white-space:nowrap">Tahu risiko sawah sebelum terlambat.</p></div>
<img src="{mascot}" width="520" height="520"></body></html>""",
            encoding="utf-8",
        )
        page.goto(og.as_uri())
        page.wait_for_timeout(800)
        page.screenshot(path=str(PUBLIC / "og-image.png"))
        browser.close()
    print("brand assets written")


if __name__ == "__main__":
    main()
