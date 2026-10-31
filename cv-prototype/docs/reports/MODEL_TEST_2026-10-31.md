# TUAI Sigap model test, 31 October 2026

Tested on public datasets through the same code the app runs. **None of these photos come from Lampung, and no PPL has reviewed the labels.** Treat this as a first screening, not the field validation in [VALIDATION.md](../VALIDATION.md).

Thresholds used: [operating-thresholds.json](../../evaluation/operating-thresholds.json). Its `calibration_manifest_sha256` hashes the raw result files of this run.

## Summary

- The original disease model was replaced because it ignored lesions on new photos.
- The new disease model is usable as a cautious screen. It says "uncertain" on most photos from a new source, and **its blast results were mostly wrong there**.
- Roboflow is strong on its own test split and reasonable on an independent planthopper set.
- No preprocessing fault explained the model failure, but an input check was wrongly rejecting small photos and has been fixed.

## Test data

| Set | Photos used | Licence | What it tells us |
| --- | --- | --- | --- |
| RiceLeafBD (Mendeley `sjkptpgv79`) | 1,000 (200 each: blast, tungro, normal, narrow brown spot, sheath blight) | CC BY 4.0 | New source. Detached leaves on a white background, so not in-field conditions |
| Rice Leaf Disease Images (Mendeley `fwcj7stb8r`) | 600 (150 each: blight, blast, brown spot, tungro) | CC BY 4.0 | In-field style, but **likely overlaps both models' training data**, so an upper bound only |
| Roboflow `rice-pest-jmdev` v1, test split | 150 for Roboflow; all 415 for the local model | CC BY 4.0 | Same project as the Roboflow model, so not independent of it |
| Roboflow `identification-planthopper` | 28 (test + valid) | CC BY 4.0 | Independent planthopper check |
| Wikimedia Commons plus insect photos | 34 + 89 | Per file | Photos that are not rice leaves |
| RiceLeafBD normal, blast, tungro | 75 | CC BY 4.0 | Pest false alarms on leaves with no insects |

## Why the disease model changed

| On RiceLeafBD | `prithivMLmods/Rice-Leaf-Disease` | `Huyt/rice-leaf-disease-efficientnet-b0` | `cvmil/dinov2-base_…_fft` |
| --- | --- | --- | --- |
| Blast called blast (top choice) | 0/200 | 62/200 | 0/200 |
| Tungro called tungro (top choice) | 0/200 | 98/200 | not a class |
| Normal called healthy (top choice) | 200/200 | 144/200 | 190/200 |
| All 1,000 photos called healthy | Yes | No | No |
| Not-a-leaf photos scoring ≥ 0.9 | 51 of 93 insect photos, plus sky, banana and others (with all views agreeing) | 0/123 | 22/123 |

`anthony2261/convnext-base-224-paddy-disease` was also tried and dropped: its published config and weights do not match, and it has no licence or model card.

The first model scored about 95% on the older set with the same preprocessing, and its failure did not change across four cropping variants. It most likely learned the background of its training photos rather than the lesions. A threshold cannot fix that, since it was at about 1.00 on every wrong answer.

## Disease results at the app's thresholds

Score at least 0.75, margin at least 0.4, and the photo and its mirror image agree. Only blight, blast, brown spot, tungro and healthy can be named.

**RiceLeafBD, 1,000 photos: 105 named, 887 uncertain, 8 asked to retake.**

| Named as | Count | Matches label | The rest were |
| --- | --- | --- | --- |
| Tungro | 16 | 13 | 2 normal, 1 blast |
| No symptom | 32 | 23 | 9 narrow brown spot |
| Blast | 50 | 5 | 28 narrow brown spot, 16 sheath blight, 1 tungro |
| Brown spot | 7 | 0 | 7 narrow brown spot |
| Blight | 0 | - | - |

Only about 1 in 20 true blast and tungro photos gets a correct name; most get "uncertain". The errors are mainly diseased leaves named as a different disease. Nine diseased leaves were named "no symptom", which is why that result always tells the user to check other leaves.

**Older set, 600 photos (likely overlaps training): 537 named, 533 of them correct.** Blight 149/150, blast 84/150, brown spot 150/150, tungro 150/150 named correctly, with 4 blast photos named brown spot. Do not quote these as field accuracy.

**Not rice leaves, 123 photos: 3 named** (all insect photos). All 34 Commons photos, including sky, fields, hands and banana leaves, came back uncertain.

## Pest results

**Roboflow, score at least 0.6.** Median response 0.39 s.

| Class | Found | False on photos without that class |
| --- | --- | --- |
| Brown planthopper | 19/20 | 0/130 |
| Green leafhopper | 18/19 | 6/131 |
| Leaf folder | 24/26 | 0/124 |
| Rice bug | 21/22 | 3/128 |
| Stem borer | 28/31 | 4/119 |
| Whorl maggot | 16/16 | 2/134 |

- Independent planthopper set: 21/28 photos.
- Leaves with no insects: 0/75 photos had a confident box.

**Local model, score at least 0.5** (used only if Roboflow fails, and first for live camera frames).

| Class | Found | False |
| --- | --- | --- |
| Brown planthopper | 19/44 | 1/371 |
| Leaf folder | 26/80 | 1/335 |
| Yellow stem borer | 40/74 | 2/341 |

- Independent planthopper set: 19/28 photos.
- It is cautious rather than sensitive, and it cannot see the other three pest types.

## Preprocessing check

| Check | Result |
| --- | --- |
| Pest ONNX vs original checkpoint, 57 photos | 24/24 detections matched, mean score drift 0.0000005, lowest box overlap 0.9999 (those photos are already 640 px, so resizing is covered separately by the 2560×1440 unit test for Roboflow and the browser run for local) |
| Disease ONNX vs original model, 60 photos | 60/60 same top class, largest probability drift 0.011 |
| Disease class-map output | Averages to the logits within 0.000001, so the highlight reflects the real decision |
| **Fault found:** disease minimum size of 224 px | Rejected about 1 in 10 of the Tungro test images sampled (39/400), although the model resizes every photo. Lowered to 160 px |
| **Fault found:** wide camera frames | Old flow showed a guide unrelated to what the model read. The guide now matches the model's center square exactly |
| **Fault found:** `prepare_models.py` | Imported a backend path that no longer exists, so the pest model could never be prepared. Fixed |

## Camera check

Tested in Chromium with real photos fed in as the camera stream, at 1280×720.

- Leaf mode: live highlight and "Terlihat: Blas" within 0.3 s; capture gave the same result.
- Pest mode: live dashed box and "Mungkin: Wereng batang cokelat" from the local model; capture through Roboflow found 2 planthoppers.
- No console errors or failed requests in any flow, and no sideways scrolling at 390 px.

**Not tested: a real phone.** Direct camera access needs HTTPS or localhost, so over plain Wi-Fi HTTP the button opens the phone's own camera app instead, and there is no live overlay.

## Known gaps

- No Lampung photos and no PPL review of labels or recommendation wording.
- RiceLeafBD has no blight or brown-spot photos, so those two classes have no test on a new source.
- The Kementan handbook was unreachable. Recommendations cite IRRI only, through archived copies.
- The Commons set is small (34 photos), so it shows a direction rather than a rate.
