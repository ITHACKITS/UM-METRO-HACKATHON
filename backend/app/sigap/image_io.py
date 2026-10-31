"""Safe in-memory image decoding for TUAI Sigap."""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from .constants import ALLOWED_IMAGE_FORMATS, MAX_COMPRESSED_BYTES, MAX_DECODED_PIXELS
from .errors import APIError

Image.MAX_IMAGE_PIXELS = MAX_DECODED_PIXELS


def _register_heif() -> None:
    """Register HEIF/HEIC support when the runtime dependency is installed."""
    try:
        from pillow_heif import register_heif_opener
    except ImportError:
        return
    register_heif_opener()


_register_heif()


@dataclass(slots=True)
class DecodedImage:
    image: Image.Image
    format: str
    file_size_bytes: int


def decode_image(data: bytes) -> DecodedImage:
    """Safely decode an upload and detach the image from its in-memory byte stream."""
    if not data:
        raise APIError(
            422,
            "empty_file",
            "Berkas foto kosong.",
            "The uploaded image is empty.",
        )
    if len(data) > MAX_COMPRESSED_BYTES:
        raise APIError(
            413,
            "file_too_large",
            "Ukuran foto melebihi batas 12 MB.",
            "The image exceeds the 12 MB upload limit.",
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as opened:
                image_format = (opened.format or "").upper()
                if image_format not in ALLOWED_IMAGE_FORMATS:
                    raise APIError(
                        415,
                        "unsupported_format",
                        "Format foto tidak didukung. Gunakan JPEG, PNG, WebP, atau HEIC.",
                        "Unsupported image format. Use JPEG, PNG, WebP, or HEIC.",
                    )

                width, height = opened.size
                if width <= 0 or height <= 0:
                    raise APIError(
                        422,
                        "invalid_dimensions",
                        "Dimensi foto tidak valid.",
                        "The image dimensions are invalid.",
                    )
                if width * height > MAX_DECODED_PIXELS:
                    raise APIError(
                        413,
                        "decoded_image_too_large",
                        "Resolusi foto melebihi batas 25 megapiksel.",
                        "The decoded image exceeds the 25 megapixel limit.",
                    )

                opened.load()
                transposed = ImageOps.exif_transpose(opened)
                detached = transposed.convert("RGB").copy()
    except APIError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise APIError(
            413,
            "decoded_image_too_large",
            "Resolusi foto melebihi batas 25 megapiksel.",
            "The decoded image exceeds the 25 megapixel limit.",
        ) from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise APIError(
            422,
            "decode_failed",
            "Foto rusak atau tidak dapat dibaca.",
            "The image is corrupt or could not be decoded.",
        ) from None

    return DecodedImage(
        image=detached, format="HEIC" if image_format == "HEIF" else image_format,
        file_size_bytes=len(data)
    )

