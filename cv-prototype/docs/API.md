# Local API contract

Base URL during development: `http://127.0.0.1:8000/api/sigap/v1`.

All human-readable messages are objects with Indonesian (`id`) and English (`en`)
strings. Clients should prefer Indonesian. This namespace is isolated from the
weather/satellite endpoints even though both run in the same FastAPI process.

## `GET /health`

Returns API state, runtime/device information, offline configuration, and separate
disease/pest readiness. Each model entry exposes the locked repository ID,
revision, artifact hash when present, and a startup/readiness error when absent.
HTTP success means the API process is reachable; clients must still inspect model
readiness for the selected mode.

```json
{
  "status": "ready | degraded",
  "service": "TUAI Sigap API",
  "version": "0.1.0",
  "offline": true,
  "runtime": {
    "python": "3.12.x",
    "platform": "Linux-...",
    "device_preference": "auto"
  },
  "calibration_status": "unavailable | partial | frozen",
  "models": [
    {
      "mode": "disease | pest",
      "id": "repository/model",
      "revision": "40-character revision",
      "state": "unavailable | unloaded | ready | error",
      "ready": false,
      "loaded": false,
      "artifact_sha256": null,
      "error": "readiness detail or null"
    }
  ]
}
```

## `GET /capabilities`

Returns supported modes/classes, bilingual labels, input constraints, model
provenance, and limitations. The endpoint is the UI's authoritative discovery
document; it does not report measured accuracy.

```json
{
  "service": "TUAI Sigap — Cek Daun & Hama",
  "models": [
    {
      "id": "repository/model",
      "revision": "40-character revision",
      "artifact_sha256": null,
      "preprocessing_version": "versioned-contract"
    }
  ],
  "modes": [
    {
      "mode": "disease | pest",
      "title": { "id": "...", "en": "..." },
      "photo_instruction": { "id": "...", "en": "..." },
      "classes": [
        {
          "class_id": "string or integer",
          "class_key": "stable_key",
          "label": { "id": "...", "en": "..." }
        }
      ]
    }
  ],
  "input_limits": {
    "formats": ["JPEG", "PNG", "WEBP", "HEIC", "HEIF"],
    "max_compressed_bytes": 12582912,
    "max_decoded_pixels": 25000000,
    "disease_min_short_side": 224,
    "pest_min_short_side": 480
  },
  "limitations": [{ "id": "...", "en": "..." }]
}
```

## `POST /analyze`

Multipart form fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `file` | yes | JPEG, PNG, WebP, HEIC, or HEIF photo, at most 12 MiB compressed and 25 MP decoded |
| `mode` | yes | Exactly `disease` or `pest` |
| `live` | no | Boolean, default `false`. Marks a camera preview frame: pest frames try the local model first, to save Roboflow credits. |

Shortest side: disease 160 px; pest 360 px. The server does not persist the file.

### Shared result

```json
{
  "status": "ok | abstain | retake",
  "mode": "disease | pest",
  "processing": "local | roboflow_cloud",
  "score_kind": "model_score",
  "model": {
    "id": "repository/model",
    "revision": "40-character revision",
    "artifact_sha256": null,
    "preprocessing_version": "versioned-contract"
  },
  "quality": {
    "width": 1280,
    "height": 960,
    "format": "JPEG",
    "file_size_bytes": 245010,
    "blur_score": 91.2,
    "mean_luminance": 116.4,
    "warnings": [
      { "code": "example", "message": { "id": "...", "en": "..." } }
    ],
    "rejection_reason": null
  },
  "limitations": [{ "id": "...", "en": "..." }],
  "next_action": { "id": "...", "en": "..." }
}
```

`blur_score` and `mean_luminance` are technical capture signals, not disease
severity. `artifact_sha256` is `null` only when no verified artifact was loaded.
`processing=roboflow_cloud` means the user explicitly allowed the photo to be sent
to Roboflow after the local pest model was unavailable; this is never silent.

### Disease member

Disease results add:

```json
{
  "disease": {
    "accepted": false,
    "candidates": [
      {
        "class_id": "blast",
        "label": { "id": "Blas", "en": "Blast" },
        "score": 0.73
      }
    ],
    "top_score": 0.73,
    "score_margin": 0.11,
    "calibration_status": "unavailable | partial | frozen",
    "consistency_status": "not_checked | stable | unstable",
    "view_count": 3,
    "top_class_agreement": 1.0,
    "top_score_spread": 0.04
  }
}
```

Candidates are model indications. The model's `healthy` class must be displayed as
“tidak ada gejala penyakit target yang dikenali pada foto ini,” not “safe” or a
definitive healthy diagnosis.

Disease inference averages the photo and its mirror image. A result is named only when
the class is one of the five measured ones, its score and margin clear
`evaluation/operating-thresholds.json`, and both views agree. `disease.heatmap` holds a
7x7 grid (0-1) over the center square the model read, and appears only on a named
disease. `disease.closest_match` appears on some uncertain results, and is never
"healthy". Every response carries `recommendations` (sourced steps per named class) or
`general_steps`.

### Pest member

Pest results add:

```json
{
  "pest": {
    "detections": [
      {
        "class_id": 7,
        "class_key": "brown_plant_hopper",
        "label": { "id": "Wereng batang cokelat", "en": "Brown planthopper" },
        "score": 0.81,
        "accepted": false,
        "bbox": { "x_min": 210.0, "y_min": 150.0, "x_max": 390.0, "y_max": 470.0 }
      }
    ],
    "image_width": 1280,
    "image_height": 960,
    "calibration_status": "unavailable | partial | frozen"
  }
}
```

Box coordinates are pixels in the EXIF-normalized image. An empty array means no
supported visible pest was detected; it does **not** show that the plant is safe.

## Errors

Errors use:

```json
{
  "detail": {
    "code": "stable_machine_code",
    "message": { "id": "Penjelasan", "en": "Explanation" }
  }
}
```

| Status | Meaning |
| --- | --- |
| `413` | compressed file exceeds 12 MiB or decoded pixel cap |
| `415` | unsupported image content/format |
| `422` | invalid mode, corrupt image, or decode/validation failure |
| `503` | selected model is not ready; never replaced by a fabricated result |

Pest photos try Roboflow first, then the local model, and `processing` records which one
answered. `503` means both failed.

Exact error text is not a stable API field; `detail.code` is.

