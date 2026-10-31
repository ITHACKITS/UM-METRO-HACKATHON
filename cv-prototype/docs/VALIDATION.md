# Validation protocol

This protocol measures the frozen prototype; it does not train new model weights.
Calibration selects abstention thresholds only. The final test remains untouched
until thresholds and manifest hashes are frozen.

## Evidence states

| State | Meaning |
| --- | --- |
| `pending` | collection/review has not finished |
| `not_testable` | there are too few independent examples for the planned claim |
| `experimental` | evidence exists but the acceptance/calibration rule was not met |
| `tested` | the exact model, manifest, thresholds, and final-test report are frozen |

Never replace a missing project result with a model-card, paper, or training-set
number. The tracked report starts pending by design.

## 1. Freeze the model contract

Record, for both modes:

- repository and full 40-character revision;
- every artifact SHA-256 and total cache size;
- runtime package versions/device;
- preprocessing version, image size, color order, normalization, and label order;
- disease processor source and pest conversion command/hash;
- threshold file hash or explicit absence;
- threshold files must lock both model revisions and preprocessing versions; a TTA,
  crop, normalization, or label-order change invalidates the old thresholds;
- cold start, warm p50/p95 latency, peak RSS, and output repeatability on the demo
  laptop.

Native disease inference remains the baseline unless warm p95 exceeds five seconds
or peak RSS exceeds 6 GiB. An ONNX/INT8 trial is accepted only if every regression
fixture preserves top-1 and mean absolute score drift is at most 0.03.

## 2. Build the manifest before splitting

For every image, calculate SHA-256 and `dhash64-v1`, then record a non-identifying
image ID, source label, canonical label, rights basis, capture session, and the
coarsest useful metadata. Do not put file paths, names, exact coordinates, consent
forms, or raw local photos in Git.

Exact duplicates are rejected. Near duplicates are manually reviewed. All images
from the same leaf, insect, plant, field visit, or camera burst share one `group_id`
and stay in one partition. Run:

```bash
cd cv-prototype/evaluation
python -m jagapadi_eval validate examples/manifest.synthetic.json
python -m jagapadi_eval audit-manifest examples/manifest.synthetic.json
```

Replace the synthetic example only with a private, frozen manifest copy that
contains hashes/metadata—not the images themselves.

## 3. Dataset roles and label harmonization

- `sharmin3`: provenance only; never evaluated or redistributed.
- `fwcj7stb8r`: regression/smoke only because training overlap is strongly likely.
- `sjkptpgv79`: external field evaluation for exact Blast, Tungro, Healthy matches.
  Narrow Brown Spot must not be mapped to Brown Spot; Sheath Blight is OOD.
- Local Lampung images: decisive audit, with consent and blinded expert labels.
- IP102/Paddy Doctor: lineage or future research under their exact applicable terms.

No near-synonym is merged without written expert approval. Conflicting expert
labels are retained as an adjudication state rather than silently resolved by the
model.

## 4. Collection target and grouping

Seek at least 20 independent examples per supported disease/pest class where
available, plus at least 40 unsupported, negative, and poor-quality images. These
are collection targets, not automatic proof of adequate statistical power. Smaller
classes are reported `not_testable` with their actual count.

Pest instances need normalized bounding boxes created by one annotator and reviewed
by a PPL/agronomist. Negative pest photos require an explicit inspection protocol;
absence cannot be inferred merely because an annotator did not draw a box.

## 5. Calibration partition

Only the grouped calibration partition selects thresholds:

- Disease: for each predicted class, choose the score/margin pair with maximum
  coverage among pairs whose selective error is no greater than 10%. If no pair
  qualifies or data are inadequate, that class remains experimental and abstains.
- Pest: choose the score threshold with maximum recall among thresholds reaching
  at least 85% precision. If none qualifies, that pest remains experimental.

Freeze the threshold JSON and SHA-256 before final testing. Do not tune capture
instructions, preprocessing, class mapping, or thresholds after viewing final-test
errors; any change creates a new version and requires a new untouched test.

## 6. Final-test measures

### Disease

Primary metric: macro-F1 over supported final-test classes. Also report:

- balanced accuracy and overall accuracy (secondary);
- per-class precision, recall, F1, and independent sample count;
- confusion matrix;
- group-aware bootstrap 95% confidence intervals that resample whole field/
  plant/session groups, not correlated images independently;
- coverage versus selective error after abstention;
- Brier score and expected calibration error labelled strictly as raw-model-score
  diagnostics, not proof of probability calibration.

### Pest

For every pest separately, report precision, recall, F1, AP, mAP@0.5, and
mAP@0.5:0.95 only when enough reviewed boxes exist. The evaluator sorts detections
by score and greedily matches each one to at most one same-image/same-class truth
box at each IoU threshold from 0.50 through 0.95. It also reports false detections
per negative image. Predictions and truth must use the same EXIF-normalized
coordinate space. When box data are too small for stable AP/mAP, report explicit
presence/absence statistics and mark box metrics `not_testable`. Never pool away an
untested class.

### Timing/resources

Report hardware/OS, cold start, model load time, warm p50/p95 request latency, peak
RSS, cache size, concurrent-request behavior, and deterministic repeat runs.

## 7. OOD and robustness audit

Measure false confident acceptance on:

- unsupported rice diseases/pests and nutrient deficiencies;
- non-rice leaves, hands, soil, sky, screenshots, and blank images;
- blur, shadows, over/underexposure, compression, rotation, occlusion, clutter, and
  multiple leaves/insects.

Paired transformations must retain the same group as their source and never cross
calibration/test. Report score/metric degradation relative to the originals. OOD
success is low false acceptance, not a lucky nearest-class label.

## 8. Product and engineering checks

Test EXIF rotation, HEIC, corrupt files, MIME spoofing, filenames with unsafe
characters, 12 MiB boundary, 25 MP boundary, decompression bombs, mode-specific
minimum resolution, offline model absence, slow inference, simultaneous requests,
cancellation, desktop/mobile camera flow, and no post-response photo persistence.

The full browser flow must have zero console errors and zero failed same-origin
requests. Scan Git history/staging for private images, precise locations, and
consent records. Run the boundary guard before every commit.

## 9. User/expert validation

One PPL/agronomist reviews every Indonesian disease/pest name and guidance sentence.
Approximately five farmers or team representatives attempt four tasks: select the
right mode, capture a usable photo, explain the result boundary, and identify the
safe next action. Record consented aggregate completion, interpretation errors,
retake rate, time, and feedback—not names or evaluators' desired answers.

Claim TKT 4 only if the integrated prototype is tested with representative field
photos and documented users. Otherwise claim TKT 3.

## 10. Report release gate

A measured claim is publishable only when it links to:

1. immutable manifest SHA-256;
2. exact model revisions and artifact hashes;
3. threshold configuration hash;
4. evaluator version/commit;
5. aggregate report with class counts and uncertainty;
6. expert terminology approval and data-rights audit.

The tracked placeholder must remain pending until all six exist.

