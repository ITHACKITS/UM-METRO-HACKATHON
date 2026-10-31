"""TUAI Sigap model and input constants."""

from __future__ import annotations

from typing import Final

DISEASE_MODEL_ID: Final = "Huyt/rice-leaf-disease-efficientnet-b0"
DISEASE_MODEL_REVISION: Final = "a12e09fd765eda2b846836a965e951151a9125f7"
DISEASE_PREPROCESSING_VERSION: Final = (
    "timm-efficientnet-b0-bicubic-crop0.875-imagenet-norm+mirror2-v1"
)

PEST_MODEL_ID: Final = "underdogquality/yolo11s-pest-detection"
PEST_MODEL_REVISION: Final = "b64a9302e50ae089e52b770fe0d054ac77c1c3d8"
PEST_PREPROCESSING_VERSION: Final = "yolo11-letterbox-640-rgb-v1"

ROBOFLOW_PEST_MODEL_ID: Final = "rice-pest-jmdev"
ROBOFLOW_PEST_MODEL_REVISION: Final = "1"
ROBOFLOW_PEST_PREPROCESSING_VERSION: Final = "roboflow-serverless-v0-jpeg-1280-v2"

MAX_COMPRESSED_BYTES: Final = 12 * 1024 * 1024
MAX_DECODED_PIXELS: Final = 25_000_000
# The model resizes every photo itself. Its 224 px input is not a floor: a 224 limit here
# wrongly rejected about 1 in 10 of the Tungro test images checked.
DISEASE_MIN_SIDE: Final = 160
PEST_MIN_SIDE: Final = 360
ALLOWED_IMAGE_FORMATS: Final = frozenset({"JPEG", "PNG", "WEBP", "HEIF", "HEIC"})

# The model's 17 outputs, in its own class order. `result=True` classes can become a
# named result. The rest stay "uncertain": seven have about 60-70 training images, and
# Hispa, Narrow Brown Spot, Sheath Blight and Leaf Scald were not reliable on photos
# the model had never seen (see cv-prototype/docs/reports/MODEL_TEST_2026-10-31.md).
DISEASE_RAW_LABELS: Final = (
    "Bacterial Blight",
    "Bacterial Streak",
    "Bakanae",
    "Brown Spot",
    "False Smut",
    "Grassy Stunt Virus",
    "Healthy",
    "Hispa",
    "Leaf Blast",
    "Leaf Scald",
    "Narrow Brown Spot",
    "Neck Blast",
    "Ragged Stunt Virus",
    "Sheath Blight",
    "Sheath Rot",
    "Stem Rot",
    "Tungro",
)

DISEASE_CLASSES: Final = {
    "bacterial_leaf_blight": {
        "id": "Hawar daun bakteri (kresek)",
        "en": "Bacterial leaf blight",
        "aliases": {"Bacterial Blight"},
        "result": True,
    },
    "blast": {
        "id": "Blas",
        "en": "Blast",
        "aliases": {"Leaf Blast", "Neck Blast"},
        "result": True,
    },
    "brown_spot": {
        "id": "Bercak cokelat",
        "en": "Brown spot",
        "aliases": {"Brown Spot"},
        "result": True,
    },
    "healthy": {
        "id": "Tidak ada gejala yang dikenali",
        "en": "No recognized symptom",
        "aliases": {"Healthy"},
        "result": True,
    },
    "tungro": {"id": "Tungro", "en": "Tungro", "aliases": {"Tungro"}, "result": True},
    "hispa": {"id": "Hispa", "en": "Hispa", "aliases": {"Hispa"}, "result": False},
    "narrow_brown_spot": {
        "id": "Bercak cokelat sempit",
        "en": "Narrow brown spot",
        "aliases": {"Narrow Brown Spot"},
        "result": False,
    },
    "sheath_blight": {
        "id": "Hawar pelepah",
        "en": "Sheath blight",
        "aliases": {"Sheath Blight"},
        "result": False,
    },
    "leaf_scald": {"id": "Hawar ujung daun", "en": "Leaf scald", "aliases": {"Leaf Scald"}, "result": False},
    "bacterial_streak": {
        "id": "Garis daun bakteri",
        "en": "Bacterial leaf streak",
        "aliases": {"Bacterial Streak"},
        "result": False,
    },
    "bakanae": {"id": "Bakanae", "en": "Bakanae", "aliases": {"Bakanae"}, "result": False},
    "false_smut": {"id": "Noda palsu", "en": "False smut", "aliases": {"False Smut"}, "result": False},
    "grassy_stunt": {
        "id": "Kerdil rumput",
        "en": "Grassy stunt",
        "aliases": {"Grassy Stunt Virus"},
        "result": False,
    },
    "ragged_stunt": {
        "id": "Kerdil hampa",
        "en": "Ragged stunt",
        "aliases": {"Ragged Stunt Virus"},
        "result": False,
    },
    "sheath_rot": {"id": "Busuk pelepah", "en": "Sheath rot", "aliases": {"Sheath Rot"}, "result": False},
    "stem_rot": {"id": "Busuk batang", "en": "Stem rot", "aliases": {"Stem Rot"}, "result": False},
}

# Keys below 100 are IP102 indices from the local detector. Keys from 100 up exist only
# in the Roboflow model. Its generic `stem-borer` label stays separate from the narrower
# yellow stem borer because it may cover other species.
PEST_CLASSES: Final = {
    0: {"key": "rice_leaf_roller", "id": "Pelipat daun (hama putih palsu)", "en": "Rice leaf folder"},
    4: {"key": "yellow_rice_borer", "id": "Penggerek batang padi kuning", "en": "Yellow rice stem borer"},
    7: {"key": "brown_plant_hopper", "id": "Wereng batang cokelat", "en": "Brown planthopper"},
    100: {"key": "green_leafhopper", "id": "Wereng hijau", "en": "Green leafhopper"},
    101: {"key": "rice_bug", "id": "Walang sangit", "en": "Rice bug"},
    102: {"key": "stem_borer", "id": "Penggerek batang", "en": "Stem borer"},
    103: {"key": "whorl_maggot", "id": "Lalat daun padi", "en": "Rice whorl maggot"},
}
LOCAL_PEST_CLASS_IDS: Final = frozenset({0, 4, 7})

# Boxes under this score are too noisy to draw (7 of 75 insect-free leaf photos passed
# it on Roboflow), so they are dropped rather than shown as candidates.
PEST_MIN_CANDIDATE_SCORE: Final = 0.25
