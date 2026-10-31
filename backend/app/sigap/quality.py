"""Capture quality signals for TUAI Sigap."""

from __future__ import annotations

import numpy as np
from PIL import Image

from .constants import DISEASE_MIN_SIDE, PEST_MIN_SIDE
from .image_io import DecodedImage
from .schemas import BilingualText, QualityReport, QualityWarning


def _text(indonesian: str, english: str) -> BilingualText:
    return BilingualText(id=indonesian, en=english)


def _warning(code: str, indonesian: str, english: str) -> QualityWarning:
    return QualityWarning(code=code, message=_text(indonesian, english))


def _metrics(image: Image.Image) -> tuple[float, float, float, float, float]:
    grayscale = image.convert("L")
    if max(grayscale.size) > 1024:
        grayscale.thumbnail((1024, 1024), Image.Resampling.BILINEAR)
    pixels = np.asarray(grayscale, dtype=np.float32)
    mean_luminance = float(pixels.mean())
    std_luminance = float(pixels.std())
    dark_fraction = float(np.mean(pixels <= 8))
    bright_fraction = float(np.mean(pixels >= 247))

    if pixels.shape[0] < 3 or pixels.shape[1] < 3:
        blur_score = 0.0
    else:
        center = pixels[1:-1, 1:-1]
        laplacian = (
            4 * center
            - pixels[:-2, 1:-1]
            - pixels[2:, 1:-1]
            - pixels[1:-1, :-2]
            - pixels[1:-1, 2:]
        )
        blur_score = float(np.var(laplacian))
    return mean_luminance, std_luminance, dark_fraction, bright_fraction, blur_score


def assess_quality(decoded: DecodedImage, mode: str) -> QualityReport:
    width, height = decoded.image.size
    mean, std, dark_fraction, bright_fraction, blur_score = _metrics(decoded.image)
    warnings: list[QualityWarning] = []
    rejection_reason: BilingualText | None = None

    minimum_side = DISEASE_MIN_SIDE if mode == "disease" else PEST_MIN_SIDE
    if min(width, height) < minimum_side:
        warnings.append(
            _warning(
                "resolution_too_low",
                f"Sisi terpendek foto harus minimal {minimum_side} piksel untuk mode ini.",
                f"The shortest side must be at least {minimum_side} pixels for this mode.",
            )
        )
        rejection_reason = _text(
            "Foto terlalu kecil untuk dinilai. Ambil ulang dari jarak yang sesuai.",
            "The image is too small to assess. Retake it from an appropriate distance.",
        )

    if mean < 35 or dark_fraction > 0.55:
        warnings.append(
            _warning(
                "underexposed",
                "Foto terlalu gelap; gunakan cahaya merata tanpa bayangan kuat.",
                "The photo is too dark; use even light without strong shadows.",
            )
        )
    if mean > 225 or bright_fraction > 0.55:
        warnings.append(
            _warning(
                "overexposed",
                "Foto terlalu terang; hindari pantulan atau cahaya langsung.",
                "The photo is too bright; avoid glare or direct light.",
            )
        )
    if blur_score < 12:
        warnings.append(
            _warning(
                "possible_blur",
                "Foto mungkin kabur; stabilkan ponsel dan fokuskan objek.",
                "The photo may be blurry; steady the phone and focus on the subject.",
            )
        )

    if rejection_reason is None and (std < 2 or mean < 8 or mean > 247):
        rejection_reason = _text(
            "Detail visual tidak cukup. Ambil ulang foto dengan fokus dan pencahayaan merata.",
            "There is not enough visual detail. Retake with focus and even lighting.",
        )

    return QualityReport(
        width=width,
        height=height,
        format=decoded.format,
        file_size_bytes=decoded.file_size_bytes,
        blur_score=round(max(blur_score, 0.0), 4),
        mean_luminance=round(min(max(mean, 0.0), 255.0), 2),
        warnings=warnings,
        rejection_reason=rejection_reason,
    )

