"""Train the TUAI Sigap brown planthopper (wereng) detector and install it at backend/models/wereng.pt.

Steps from the concept paper:
  1. optional pre-training on IP102 boxes (academic use only),
  2. training on the Roboflow "identification-planthopper" set (CC BY 4.0), then on partner photos,
  3. testing on field photos never used for training (target mAP50 >= 0.70).

Each dataset is a YOLO export with a data.yaml (Roboflow: Export > YOLOv8).

  python scripts/sigap/train_wereng.py --data path/to/planthopper/data.yaml [--pretrain ip102/data.yaml] [--field-test mitra/data.yaml]

Ultralytics is AGPL-3.0: the project code stays open, or a paid Enterprise licence is needed.
"""

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

OUT = Path(__file__).resolve().parents[2] / "backend" / "models" / "wereng.pt"


def train(weights: str, data: str, epochs: int, imgsz: int, name: str) -> Path:
    model = YOLO(weights)
    r = model.train(data=data, epochs=epochs, imgsz=imgsz, name=name, exist_ok=True, patience=20)
    return Path(r.save_dir) / "weights" / "best.pt"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="planthopper data.yaml (Roboflow export, plus partner photos if any)")
    ap.add_argument("--pretrain", help="IP102 detection data.yaml for a first pass")
    ap.add_argument("--field-test", help="data.yaml of partner field photos never used in training")
    ap.add_argument("--base", default="yolov8n.pt")
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--imgsz", type=int, default=960, help="small insects need a larger input size")
    a = ap.parse_args()

    weights = a.base
    if a.pretrain:
        weights = str(train(weights, a.pretrain, a.epochs, a.imgsz, "wereng-pretrain"))
    best = train(weights, a.data, a.epochs, a.imgsz, "wereng")

    m = YOLO(str(best))
    val = m.val(data=a.data, imgsz=a.imgsz)
    print(f"validation mAP50 {val.box.map50:.3f}")
    if a.field_test:
        ft = m.val(data=a.field_test, imgsz=a.imgsz, split="test")
        print(f"FIELD TEST mAP50 {ft.box.map50:.3f} (target >= 0.70)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, OUT)
    print(f"installed {OUT}; restart the API to load it")


if __name__ == "__main__":
    main()
