"""Content and perceptual hashes used before any calibration/test split."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps


def hash_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 of a file without loading it all into memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def perceptual_hash(path: str | Path, size: int = 9) -> str:
    """Return a 64-bit difference hash after EXIF orientation normalization.

    dHash is intentionally named in every manifest (`dhash64-v1`). It is a
    near-duplicate screening aid, not proof that two agronomic observations are
    independent. Capture-session and plant-level grouping still takes priority.
    """

    if size < 2:
        raise ValueError("size must be at least 2")
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("L").resize(
            (size, size - 1), Image.Resampling.LANCZOS
        )
        get_pixels = getattr(image, "get_flattened_data", image.getdata)
        pixels = list(get_pixels())
    width = size
    bits = []
    for row in range(size - 1):
        offset = row * width
        bits.extend(
            pixels[offset + column] > pixels[offset + column + 1]
            for column in range(width - 1)
        )
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    hex_width = (len(bits) + 3) // 4
    return f"{value:0{hex_width}x}"


def hamming_distance(first: str, second: str) -> int:
    """Return bit distance between equally sized hexadecimal hashes."""

    if len(first) != len(second):
        raise ValueError("hashes must have equal length")
    try:
        return (int(first, 16) ^ int(second, 16)).bit_count()
    except ValueError as exc:
        raise ValueError("hashes must be hexadecimal") from exc

