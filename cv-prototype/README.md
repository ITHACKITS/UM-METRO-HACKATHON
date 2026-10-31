# TUAI Sigap — Cek Daun & Hama

A mobile-first TUAI Sigap prototype for screening rice-leaf symptoms and three visible
rice pests from a phone photo. It is a separate feature boundary inside the canonical
TUAI web/API runtime, alongside—not mixed with—the weather/satellite workflows.

Independent does not mean visually unrelated: this prototype uses the same TUAI
React/FastAPI family, paper-and-felt design system, teal/sage/grain palette, typography,
logo language, bilingual voice, provenance, and uncertainty principles. The precise
shared-versus-separate contract is in [docs/COHERENCE.md](docs/COHERENCE.md).

Every result is an **indikasi model** (model indication), not a field diagnosis. The
prototype does not estimate severity, prove that a crop is safe, detect hidden insects,
or recommend pesticide products or doses.

## What is implemented

- Two explicit photo modes with different instructions:
  - leaf symptoms: bacterial leaf blight/kresek, blast, brown spot, tungro, and
    “no target symptom recognized”;
  - visible pests: rice leaf roller, yellow rice stem borer, and brown planthopper.
- Canonical React/Vite UI at `/sigap` on port `5173`, backed by the isolated
  `/api/sigap/v1` FastAPI namespace on port `8000`.
- Safe in-memory decoding for JPEG, PNG, WebP, and HEIC; EXIF correction, 12 MB and
  25 MP limits, minimum resolution, and exposure/blur guidance.
- Lazy, offline model adapters: pinned SigLIP2 disease inference and ONNX Runtime pest
  detection. The application runtime never opens the source `.pt` pickle.
- Optional, consent-gated Roboflow serverless pest fallback for
  `rice-pest-jmdev/1`. Local ONNX is always tried first; the fallback is disabled by
  default and never receives a photo without a request-level opt-in.
- Honest abstention: without a frozen local calibration file, candidates may be shown
  as model scores but are not accepted as validated results.
- Disease hardening: explicit close-up-leaf confirmation plus batched full/mirrored/
  centered-crop consistency. Unstable views cannot be accepted, and abstained raw
  scores are de-emphasized as technical evidence rather than confidence percentages.
- Exact model revisions/hashes, preparation and offline preflight, source-vs-ONNX
  conversion checks, evaluation manifests, threshold selection, aggregate reporting,
  tests, and a staged-file boundary guard.

Model weights, private photos, consent records, and generated reports are intentionally
not in Git.

## Current evidence status

The software path can be tested with synthetic fixtures, but no project performance
claim is complete until the team supplies consented, independently labelled Lampung
photos and an agronomy/PPL reviewer. The model-card number is not TUAI accuracy.
Classes without sufficient independent examples remain `not_testable`.

## First-time setup

The commands below assume Fedora/Linux, Python 3.12, Node 20+, and npm 10+.

```bash
cd /path/to/UM-METRO-HACKATHON
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch==2.6.0 \
  --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m pip install -e './cv-prototype/evaluation[dev]'
npm --prefix frontend install
```

The explicit PyTorch command selects the CPU build and avoids downloading several
gigabytes of unused CUDA libraries on the Fedora demo laptop. If the final demo machine
has a supported NVIDIA GPU, choose the matching PyTorch 2.6.0 build deliberately and
record that runtime in the benchmark report; do not silently change the model version.

This runtime environment contains only safetensors/PyTorch for disease inference and
ONNX Runtime for pest inference. Ultralytics is preparation-only.

## Prepare the pinned models

Model preparation needs internet once. Create a separate disposable environment:

```bash
python3.12 -m venv .model-tools-venv
.model-tools-venv/bin/python -m pip install --upgrade pip
.model-tools-venv/bin/pip install torch==2.6.0 \
  --index-url https://download.pytorch.org/whl/cpu
.model-tools-venv/bin/pip install -r requirements-model-tools.txt
```

Download and verify only the three required disease files:

```bash
.model-tools-venv/bin/python scripts/prepare_models.py disease
```

The pest source is a hash-pinned pickle checkpoint. Loading any third-party pickle can
execute code. Use the disposable environment with no credentials or unrelated data,
and provide one or more licensed/consented fixture photos for parity checking:

```bash
.model-tools-venv/bin/python scripts/prepare_models.py pest \
  --acknowledge-pickle-risk \
  --fixture /absolute/path/to/licensed-pest-photo-1.jpg \
  --fixture /absolute/path/to/licensed-pest-photo-2.jpg
```

The converter verifies the source SHA-256, validates the ONNX graph, compares supported
detections, boxes, and score drift through both Ultralytics export inference and the
actual TUAI Sigap runtime decoder, copies only `.models/pest/model.onnx`, records local
provenance, and deletes the temporary `.pt`. At least one fixture must produce a
supported detection. If fixtures are omitted, the conversion is marked
`graph_only_not_demo_ready` and final preflight fails.

Verify that the complete runtime is ready with the network disconnected:

```bash
JAGAPADI_CV_OFFLINE=1 ../.venv/bin/python scripts/preflight.py
```

## Run locally

From the repository root, start the one canonical API and web development server:

```bash
npm run dev
```

Open:

- TUAI home/weather prototype: <http://127.0.0.1:5173/>
- TUAI Sigap CV prototype: <http://127.0.0.1:5173/sigap>
- Sigap API health: <http://127.0.0.1:8000/api/sigap/v1/health>
- Interactive API contract: <http://127.0.0.1:8000/docs>

Stop both with `Ctrl+C`. Uploaded bytes and decoded images are released after each
request; the prototype has no upload or history directory at runtime.

### Optional Roboflow pest fallback

The local pest ONNX remains the preferred path. If it is unavailable, an operator may
enable the external fallback in `backend/.env`:

```dotenv
TUAI_SIGAP_ROBOFLOW_FALLBACK=1
ROBOFLOW_API_KEY=replace-with-a-rotated-key
TUAI_SIGAP_ROBOFLOW_MODEL_ID=rice-pest-jmdev/1
```

Never commit the key. Pest requests still use the cloud only when the UI checkbox sends
`allow_remote_fallback=true`. The fallback maps only `brown-planthopper` and
`leaf-folder`; its generic `stem-borer` output is intentionally ignored because it
cannot substantiate the narrower yellow-rice-borer label. Cloud operation requires
network access and is reported in result provenance and limitations.

### Run only one side

```bash
cd /path/to/UM-METRO-HACKATHON
npm run dev:api
```

```bash
npm --prefix frontend run dev
```

The root Vite development server proxies `/api` to `127.0.0.1:8000`.

## API summary

| Endpoint | Purpose |
|---|---|
| `GET /api/sigap/v1/health` | Runtime, offline flag, readiness, revisions, hashes, and load errors. |
| `GET /api/sigap/v1/capabilities` | Supported modes/classes, bilingual labels, input limits, and limitations. |
| `POST /api/sigap/v1/analyze` | Multipart fields `file` and `mode=disease\|pest`. |

Analysis responses are a discriminated union with `status=ok|abstain|retake`. Every
response includes image quality, model revision/hash, `score_kind=model_score`,
limitations, and a safe next action. See [docs/API.md](docs/API.md) for examples.

## Run source-level tests

Tests do not need real model weights; adapters are replaced with deterministic fakes.

```bash
../.venv/bin/python scripts/verify.py
```

Or run components separately:

```bash
cd ../backend && ../.venv/bin/python -m pytest -q tests/sigap
cd ../cv-prototype && ../.venv/bin/python -m pytest -q evaluation/tests
cd ../frontend && npm run typecheck && npm run test && npm run build
```

The boundary guard is also available directly:

```bash
python3.12 scripts/check_boundary.py
```

It fails if model/private artifacts are staged or if root `CONTEXT.md` becomes
tracked/ignored. Use explicit `git add` paths; never use `git add -A`.

## Calibration and evaluation

Do not create thresholds from demo photos or the final test partition. Follow this order:

1. Obtain consent, anonymize identifiers, and have a PPL/agronomist label the photos.
2. Build and validate the private immutable manifest.
3. Exact/perceptually deduplicate, then group by leaf, insect, plant, burst, and visit.
4. Split groups into calibration and final-test partitions.
5. Select thresholds only on calibration data.
6. Freeze threshold JSON plus dataset hashes before opening the final test results.
7. Generate aggregate reports; never commit private photos or identifying metadata.

Evaluation commands and schemas are in [evaluation/README.md](evaluation/README.md).
Scientific rules, test targets, and report status are in
[docs/VALIDATION.md](docs/VALIDATION.md).

## Performance check on the demo laptop

With the API running and a private manifest-backed image available:

```bash
../.venv/bin/python scripts/benchmark.py \
  --mode disease \
  --image /absolute/path/to/consented-leaf.jpg \
  --runs 12 \
  --server-pid API_PROCESS_ID \
  --output benchmarks/generated/disease-demo-laptop.json
```

Repeat for pest mode. The first call is reported as cold; later calls produce warm p50
and p95. No latency or memory number should enter the pitch until this command has been
run on the actual demo laptop and its aggregate output has been reviewed.

## Before field use or Demo Day

The team still needs to provide:

- a named PPL/agronomy reviewer, role, review date, and approved terminology;
- consented local photos and blinded labels, with pest bounding boxes where applicable;
- enough independent samples per class, plus unsupported and poor-quality photos;
- completed calibration/final-test manifests and aggregate reports;
- task-based sessions with the expert and about five intended users;
- a network-off rehearsal, prewarmed models, and a 3–5 minute backup video.

Use [docs/DEMO_CHECKLIST.md](docs/DEMO_CHECKLIST.md),
[docs/CONSENT_TEMPLATE.md](docs/CONSENT_TEMPLATE.md), and
[docs/TERMINOLOGY_REVIEW.md](docs/TERMINOLOGY_REVIEW.md). Until those records exist,
report the implementation as an experimental prototype and leave validation fields
pending.

## Folder map

```text
cv-prototype/
├── evaluation/       private-manifest schemas, metrics, calibration, and reports
├── docs/             architecture, safety, licences, validation, and demo records
├── scripts/          preparation, preflight, benchmark, verification, and boundary guard
├── .models/          generated local model cache (ignored; created during preparation)
└── model-lock.json   tracked immutable source revisions, hashes, labels, and conversion contract
```

Runtime code lives only in root `frontend/src/sigap/`, `backend/app/sigap/`, and
`backend/tests/sigap/`. Weather-derived `forecast_suitability` remains distinct from
photo-derived `visual_observation`; the shared process and ports do not fuse evidence.

