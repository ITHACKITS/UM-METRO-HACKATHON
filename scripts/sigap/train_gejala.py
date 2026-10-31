"""Train the TUAI Sigap pest-symptom classifier on Paddy Doctor and install it at backend/models/gejala_hama.pt.

Paddy Doctor (Petchiammal et al., 2023) ships train_images/<class>/*.jpg. Only the pest-symptom
classes and the healthy class are kept; leaf diseases are handled by the Hugging Face model.
The dataset has no stated licence: ask the authors before using it beyond research.

  python scripts/sigap/train_gejala.py --paddy-doctor path/to/train_images [--field-test path/to/mitra_gejala]

--field-test is a folder of partner photos in the same <class>/ layout, never used for training.
The concept paper targets F1 >= 0.80 per symptom class on those photos.
"""

import argparse
import random
import shutil
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend" / "models" / "gejala_hama.pt"
# Paddy Doctor folder -> class name the API maps (see backend/app/sigap/models.py SYMPTOM_KEYS).
KEEP = {"dead_heart": "dead_heart", "hispa": "hispa", "leaf_folder": "leaf_folder", "normal": "normal"}


def build(src: Path, dst: Path, val_share: float = 0.2) -> None:
    random.seed(7)
    for folder, cls in KEEP.items():
        files = sorted((src / folder).glob("*.jpg")) if (src / folder).exists() else []
        if not files:
            print(f"skip {folder}: not in {src}")
            continue
        random.shuffle(files)
        cut = int(len(files) * (1 - val_share))
        for split, part in (("train", files[:cut]), ("val", files[cut:])):
            d = dst / split / cls
            d.mkdir(parents=True, exist_ok=True)
            for f in part:
                shutil.copy(f, d / f.name)
        print(f"{cls}: {cut} train, {len(files) - cut} val")


def f1_per_class(model: YOLO, folder: Path) -> None:
    names = model.names
    stats = {c: [0, 0, 0] for c in names.values()}  # tp, fp, fn
    for cdir in sorted(p for p in folder.iterdir() if p.is_dir()):
        for img in cdir.glob("*.*"):
            pred = names[int(model(str(img), verbose=False)[0].probs.top1)]
            if pred == cdir.name:
                stats[cdir.name][0] += 1
            else:
                stats.setdefault(cdir.name, [0, 0, 0])[2] += 1
                stats[pred][1] += 1
    for c, (tp, fp, fn) in stats.items():
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        print(f"FIELD TEST {c}: F1 {f1:.2f} (tp {tp}, fp {fp}, fn {fn}; target >= 0.80)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paddy-doctor", required=True, type=Path)
    ap.add_argument("--field-test", type=Path)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--work", type=Path, default=ROOT / "backend" / "data" / "train-gejala")
    a = ap.parse_args()

    if a.work.exists():
        shutil.rmtree(a.work)
    build(a.paddy_doctor, a.work)
    r = YOLO("yolov8n-cls.pt").train(data=str(a.work), epochs=a.epochs, imgsz=320, name="gejala", exist_ok=True)
    best = Path(r.save_dir) / "weights" / "best.pt"
    if a.field_test:
        f1_per_class(YOLO(str(best)), a.field_test)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, OUT)
    print(f"installed {OUT}; restart the API to load it")


if __name__ == "__main__":
    main()
