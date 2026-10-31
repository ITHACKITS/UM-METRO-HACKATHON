"""Retest the leaf-disease model on photos it was not trained on, as the concept paper requires.

The published 94.77% accuracy of prithivMLmods/Rice-Leaf-Disease was likely measured on its own
training data. Run this on Rice Leaf Disease Image Samples (Mendeley, CC BY 4.0), RiceLeafBD field
photos (CC BY 4.0) or partner photos, laid out as <folder>/<class>/*.jpg. Folder names are matched
loosely: blight/kresek, blast/blas, brown/bercak, tungro, healthy/sehat.

  python scripts/sigap/eval_disease.py path/to/test_folder
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.sigap import models
from PIL import Image

ALIASES = {"kresek": "kresek", "blight": "kresek", "blas": "blas", "blast": "blas", "brown": "bercak_coklat", "bercak": "bercak_coklat", "tungro": "tungro", "healthy": "sehat", "sehat": "sehat", "normal": "sehat"}


def truth(name: str) -> str | None:
    n = name.lower().replace(" ", "").replace("_", "")
    return next((v for k, v in ALIASES.items() if k in n), None)


def main(folder: Path) -> None:
    tp, fp, fn = Counter(), Counter(), Counter()
    confusion = Counter()
    for cdir in sorted(p for p in folder.iterdir() if p.is_dir()):
        t = truth(cdir.name)
        if not t:
            print(f"skip folder {cdir.name}: unknown class")
            continue
        for img in sorted(cdir.glob("*.*")):
            try:
                r = models.disease(Image.open(img).convert("RGB"))
            except OSError as e:  # not an image
                print(f"skip {img.name}: {e}")
                continue
            if r["status"] != "ok":
                sys.exit(f"model unavailable: {r['reason']}")
            p = r["top"]["key"]
            confusion[(t, p)] += 1
            if p == t:
                tp[t] += 1
            else:
                fn[t] += 1
                fp[p] += 1
    classes = sorted(set(tp) | set(fn) | set(fp))
    total = sum(confusion.values())
    print(f"\n{total} photos, accuracy {sum(tp.values()) / total:.3f}" if total else "no photos")
    for c in classes:
        f1 = 2 * tp[c] / (2 * tp[c] + fp[c] + fn[c]) if tp[c] else 0.0
        print(f"{c:15s} F1 {f1:.2f}  (tp {tp[c]}, fp {fp[c]}, fn {fn[c]}; target >= 0.80)")
    print("\nconfusion (truth -> predicted):")
    for (t, p), n in sorted(confusion.items()):
        if t != p:
            print(f"  {t} -> {p}: {n}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
