# Third-party notices

This file is a provenance checklist, not legal advice. Exact dependency versions
and licences must be regenerated from the final lockfiles before release.

## Models

### Rice leaf disease classifier

- Source: <https://huggingface.co/Huyt/rice-leaf-disease-efficientnet-b0>
- Revision: `a12e09fd765eda2b846836a965e951151a9125f7`
- Repository licence statement: Apache License 2.0
- Required notice: retain the Apache-2.0 licence/notice associated with downloaded
  artifacts.
- Risk: the model card does not state the licence of its training dataset. Do not imply
  commercial clearance until that is confirmed.

### Rice pest detector

- Source: <https://huggingface.co/underdogquality/yolo11s-pest-detection>
- Revision: `b64a9302e50ae089e52b770fe0d054ac77c1c3d8`
- Third-party repository licence statement: MIT
- Runtime artifact: locally converted ONNX with recorded source and output hashes.
- Risk: training lineage is IP102, whose repository limits images to academic use.
  No IP102 images are bundled or redistributed.
- Unresolved conflict: the current official
  [Ultralytics licence page](https://www.ultralytics.com/license) says Ultralytics
  YOLO code/models are AGPL-3.0 by default and proprietary/commercial deployment
  may require Enterprise terms. The third-party MIT statement cannot be assumed to
  override upstream obligations. Commercial/distributed use is blocked pending
  licensor/legal clarification, full compliance, or model replacement.

### Roboflow hosted pest detector

- Source project: <https://universe.roboflow.com/capstone-aedws/rice-pest-jmdev>
- Hosted model ID: `rice-pest-jmdev/1`
- Project licence statement: CC BY 4.0
- Runtime role: first choice for pest photos when a key is set. The submitted photo
  leaves the local device.
- Outputs: all six hosted labels. Generic `stem-borer` stays separate from the local
  yellow-rice-borer class.

### Conversion tooling

Ultralytics tooling is used only in a disposable preparation environment to load
the third-party pickle checkpoint and export ONNX. It is not a production runtime
dependency. Converter-only use and ONNX output do not automatically erase source
model/code obligations. Before distributing a converter environment, converted
artifact, service, or product, the team must review the exact installed version,
upstream model provenance, and applicable licence terms or replace the detector.

## Datasets

- Rice Leaf Disease Image Samples (`fwcj7stb8r`): CC BY 4.0; regression only.
- RiceLeafBD (`sjkptpgv79`): CC BY 4.0; exact-match field audit only.
- Paddy Doctor: use deferred until artifact-specific terms are confirmed.
- IP102: academic evaluation/lineage only; images not distributed.
- `sharmin3/Rice-Leaf-Disease`: no declared licence; documentation only.
- Roboflow `rice-pest-jmdev/1`: hosted detector; no source images are bundled.

See [DATA_AND_LICENSES.md](DATA_AND_LICENSES.md) for the binding project roles.

## Software families to verify from final lockfiles

- FastAPI, Uvicorn, Pydantic, python-multipart
- Pillow and optional HEIF decoder
- PyTorch, Transformers, Hugging Face Hub
- ONNX Runtime and NumPy
- React, TypeScript, Vite, and their transitive packages

The final notice bundle must record package name, locked version, source URL,
SPDX identifier, copyright/notice requirements, and whether it ships at runtime.
No dependency's presence should be inferred from this checklist alone.

