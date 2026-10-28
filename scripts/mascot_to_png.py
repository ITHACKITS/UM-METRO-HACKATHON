"""Cut the felt mascot out of its peach studio background.

The backdrop is modelled as a smooth colour field (quadratic fit to the border
pixels), so its gradient and vignette do not leak into the matte. Alpha comes
from colour distance in Lab with lightness down-weighted, which keeps the floor
shadow out while felt fibres keep soft edges. Edge colours are then
decontaminated so no peach halo shows on dark or light pages.

Usage: python scripts/mascot_to_png.py assets/mascot-source frontend/public/mascot
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

SIZES = [64, 128, 256, 512, 1024]


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def fit_background(img: np.ndarray, border: int = 40) -> np.ndarray:
    h, w, _ = img.shape
    mask = np.zeros((h, w), bool)
    mask[:border], mask[-border:], mask[:, :border], mask[:, -border:] = True, True, True, True
    yy, xx = np.mgrid[0:h, 0:w]
    x, y = xx / w - 0.5, yy / h - 0.5
    A = np.stack([np.ones_like(x), x, y, x * x, y * y, x * y], -1)
    coef, *_ = np.linalg.lstsq(A[mask], img[mask], rcond=None)
    return A @ coef


def cut(path: Path) -> Image.Image:
    img = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    bg = np.clip(fit_background(img), 0, 255)
    lab, lab_bg = srgb_to_lab(img), srgb_to_lab(bg)
    d = lab - lab_bg
    # Lightness differences are mostly shadow and vignette; chroma separates felt from backdrop.
    dist = np.sqrt((0.35 * d[..., 0]) ** 2 + d[..., 1] ** 2 + d[..., 2] ** 2)
    lo, hi = 9.0, 22.0
    alpha = np.clip((dist - lo) / (hi - lo), 0, 1)
    alpha = alpha * alpha * (3 - 2 * alpha)

    # Keep the mascot: the largest solid component plus anything touching it.
    solid = alpha > 0.5
    solid = ndimage.binary_closing(solid, iterations=3)
    lab_ids, n = ndimage.label(solid)
    if n:
        sizes = ndimage.sum(solid, lab_ids, range(1, n + 1))
        keep_ids = [i + 1 for i, s in enumerate(sizes) if s >= 0.02 * sizes.max()]
        body = np.isin(lab_ids, keep_ids)
        # Fill only small holes (eyes, button shading); large gaps between blades are backdrop.
        holes = ndimage.binary_fill_holes(body) & ~body
        hole_ids, nh = ndimage.label(holes)
        if nh:
            hs = ndimage.sum(holes, hole_ids, range(1, nh + 1))
            hd = ndimage.mean(dist, hole_ids, range(1, nh + 1))
            # Tiny holes are always filled; mid-size ones only if they are not pure backdrop colour.
            small = [i + 1 for i, (s, m) in enumerate(zip(hs, hd)) if s < 0.0003 * body.size or (s < 0.0025 * body.size and m > 5.0)]
            filled = np.isin(hole_ids, small)
            body = body | filled
            alpha = np.where(ndimage.binary_dilation(filled, iterations=2), 1.0, alpha)
        near = ndimage.binary_dilation(body, iterations=6)
        alpha = np.where(near, alpha, 0.0)
        alpha = np.where(ndimage.binary_erosion(body, iterations=3), 1.0, alpha)

    # Decontaminate: remove the backdrop colour that bleeds into semi-transparent fibres.
    a3 = alpha[..., None]
    fg = np.where(a3 > 0.02, (img - (1 - a3) * bg) / np.maximum(a3, 0.02), img)
    fg = np.clip(fg, 0, 255)
    rgba = np.concatenate([fg, alpha[..., None] * 255], -1).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    return out.crop(out.getbbox())


def pad_square(im: Image.Image, margin: float = 0.06) -> Image.Image:
    w, h = im.size
    side = int(max(w, h) * (1 + 2 * margin))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    return canvas


def avatar(im: Image.Image) -> Image.Image:
    # Head and scarf: the top ~62% of the figure, centred on the face.
    w, h = im.size
    top = im.crop((0, 0, w, int(h * 0.62)))
    return pad_square(top, 0.04)


def main(src: str, dst: str) -> None:
    out_dir = Path(dst)
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(Path(src).glob("*.jpg")):
        name = f.stem
        im = pad_square(cut(f))
        im.save(out_dir / f"{name}.png", optimize=True)
        for s in SIZES:
            im.resize((s, s), Image.LANCZOS).save(out_dir / f"{name}-{s}.png", optimize=True)
            if s <= 512:
                im.resize((s * 2, s * 2), Image.LANCZOS).save(out_dir / f"{name}-{s}@2x.png", optimize=True)
        av = avatar(cut(f))
        for s in (64, 128, 256):
            av.resize((s, s), Image.LANCZOS).save(out_dir / f"{name}-avatar-{s}.png", optimize=True)
        print(f"{f.name}: {im.size}")


if __name__ == "__main__":
    main(*(sys.argv[1:3] if len(sys.argv) >= 3 else ("assets/mascot-source", "frontend/public/mascot")))
