#!/usr/bin/env bash
# Convert the pinned pest checkpoint to ONNX inside a container.
#
# best.pt is a pickle file, and loading a pickle can run code. So the conversion runs in
# Podman with no network, no capabilities, and only a temporary folder mounted: it cannot
# see backend/.env or the rest of this repository. Only model.onnx is copied back.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REVISION=b64a9302e50ae089e52b770fe0d054ac77c1c3d8
SHA=810f0df179aec54f5d9762a11df4a147ff87ef79ca46649151914eeed260237f
IMAGE=docker.io/library/python:3.12-slim
WORK="$(mktemp -d "${TMPDIR:-/tmp}/tuai-pest-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

curl -fsSL -o "$WORK/best.pt" \
  "https://huggingface.co/underdogquality/yolo11s-pest-detection/resolve/$REVISION/best.pt"
echo "$SHA  $WORK/best.pt" | sha256sum -c -

cat > "$WORK/req.txt" <<'REQ'
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.6.0+cpu
torchvision==0.21.0+cpu
ultralytics==8.3.221
onnx==1.17.0
onnxruntime==1.21.0
numpy==2.2.6
REQ
cat > "$WORK/convert.py" <<'PY'
import os, shutil, sys
sys.path.insert(0, "/w/pip")
os.environ["YOLO_CONFIG_DIR"] = "/tmp/u"
from ultralytics import YOLO
import onnx
path = YOLO("/w/best.pt").export(
    format="onnx", opset=17, imgsz=640, dynamic=False, simplify=False, half=False, device="cpu"
)
onnx.checker.check_model(onnx.load(path))
shutil.copy(path, "/w/model.onnx")
PY

# Installing needs the network but does not touch best.pt's contents.
podman run --rm -v "$WORK:/w:Z" "$IMAGE" sh -c \
  'pip install -q --target /w/pip -r /w/req.txt \
   && rm -rf /w/pip/cv2 /w/pip/opencv_python* \
   && pip install -q --no-deps --target /w/pip opencv-python-headless==4.11.0.86'
podman run --rm --network=none --cap-drop=all --security-opt=no-new-privileges \
  -v "$WORK:/w:Z" "$IMAGE" python /w/convert.py

mkdir -p "$HERE/.models/pest"
cp "$WORK/model.onnx" "$HERE/.models/pest/model.onnx"
sha256sum "$HERE/.models/pest/model.onnx"
