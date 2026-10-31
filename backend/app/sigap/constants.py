"""Frozen TUAI Sigap model and input constants."""

from __future__ import annotations

from typing import Final

DISEASE_MODEL_ID: Final = "prithivMLmods/Rice-Leaf-Disease"
DISEASE_MODEL_REVISION: Final = "170d10e070c308e0e5337690d67371825591f35b"
DISEASE_PREPROCESSING_VERSION: Final = (
    "hf-auto-image-processor-slow@revision+exif-rgb+tta3-consistency-v2"
)

PEST_MODEL_ID: Final = "underdogquality/yolo11s-pest-detection"
PEST_MODEL_REVISION: Final = "b64a9302e50ae089e52b770fe0d054ac77c1c3d8"
PEST_PREPROCESSING_VERSION: Final = "yolo11-letterbox-640-rgb-v1"

ROBOFLOW_PEST_MODEL_ID: Final = "rice-pest-jmdev"
ROBOFLOW_PEST_MODEL_REVISION: Final = "1"
ROBOFLOW_PEST_PREPROCESSING_VERSION: Final = "roboflow-serverless-v0-jpeg-v1"

MAX_COMPRESSED_BYTES: Final = 12 * 1024 * 1024
MAX_DECODED_PIXELS: Final = 25_000_000
DISEASE_MIN_SIDE: Final = 224
PEST_MIN_SIDE: Final = 480
ALLOWED_IMAGE_FORMATS: Final = frozenset({"JPEG", "PNG", "WEBP", "HEIF", "HEIC"})

DISEASE_CLASSES: Final = {
    "bacterial_leaf_blight": {
        "id": "Hawar daun bakteri/kresek",
        "en": "Bacterial leaf blight",
        "aliases": {
            "bacterialblight",
            "bacterial blight",
            "bacterial_blight",
            "bacterial_leaf_blight",
            "bacterial leaf blight",
        },
    },
    "blast": {"id": "Blas", "en": "Blast", "aliases": {"blast"}},
    "brown_spot": {
        "id": "Bercak cokelat",
        "en": "Brown spot",
        "aliases": {"brownspot", "brown spot", "brown_spot"},
    },
    "healthy": {
        "id": "Tidak ada gejala target yang dikenali",
        "en": "No target disease symptom recognized",
        "aliases": {"healthy", "normal"},
    },
    "tungro": {"id": "Tungro", "en": "Tungro", "aliases": {"tungro"}},
}

PEST_CLASSES: Final = {
    0: {
        "key": "rice_leaf_roller",
        "id": "Hama putih palsu/penggulung daun padi",
        "en": "Rice leaf roller",
    },
    4: {
        "key": "yellow_rice_borer",
        "id": "Penggerek batang padi kuning",
        "en": "Yellow rice stem borer",
    },
    7: {
        "key": "brown_plant_hopper",
        "id": "Wereng batang cokelat",
        "en": "Brown planthopper",
    },
}

