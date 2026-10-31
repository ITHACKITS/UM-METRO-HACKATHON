# Limitations and claim boundary

## What this prototype can show

Given a suitable phone photo, the system can expose an **indikasi model** for five
disease-classifier outputs and boxes for three supported visible pest classes. It
also explains capture-quality problems and can abstain.

This is a technical baseline for field testing, not a diagnostic device.

## What it cannot establish

- It cannot provide a definitive disease or pest diagnosis.
- It cannot detect an infection before visible symptoms exist.
- It cannot estimate severity, affected area, yield loss, or infestation density.
- It cannot identify hidden insects, eggs, larvae inside stems, or pests inferred
  only from damage.
- It cannot exclude unsupported diseases, pests, nutrient deficiencies, chemical
  damage, drought stress, or other look-alike conditions.
- “No detection” does not mean safe. The classifier's healthy class means only
  that no target symptom was recognized in that photo.
- It cannot prescribe a pesticide, active ingredient, dose, spray schedule, or
  autonomous field treatment.
- It does not associate an observation with a farmer, field block, map, alert, or
  the existing weather-risk prototype.

## Model-specific limitations

The disease model is closed-set: it always distributes scores across bacterial
leaf blight, blast, brown spot, healthy, and tungro. There is no learned unknown
class. Its advertised 94.77% is not independent TUAI performance and must not
appear as such.

TUAI therefore requires the user to confirm a close-up single-leaf subject and runs
three-view consistency inference. This reduces accidental mode misuse and rejects
unstable crops, but the confirmation is human-provided and the consistency check is not
an automatic `not_a_leaf` detector. A consistently overconfident unsupported image may
still rank a disease highly; while calibration is unavailable it remains abstained and
its raw scores are shown only as technical detail.

The pest detector inherits IP102's domain and taxonomy. Only source indices 0, 4,
and 7 are exposed. Small, hidden, blurred, occluded, or differently staged insects
may be missed, and background objects may cause false detections. IP102's stated
academic-use restriction is a commercialization risk. The third-party model's MIT
statement also conflicts with current Ultralytics upstream licensing information;
commercial/distributed use requires licensor/legal clarification or replacement.

If the optional Roboflow serverless fallback is deliberately enabled, it is an online
contingency rather than an offline model. A pest photo is sent to a third-party service
only after the user checks the per-request consent control. Only `brown-planthopper`
and `leaf-folder` have safe mappings to the locked TUAI taxonomy. The hosted model's
generic `stem-borer` output is ignored because it does not establish the yellow-rice-
stem-borer species. No hosted metric is TUAI accuracy, and cloud failure still produces
an unavailable result rather than a fabricated local prediction.

The two selected models are baselines. The disease training lineage lacks a clear
licence for the named Hugging Face dataset, and neither model has yet been proven
on representative Lampung fields.

## Evidence state

Before a frozen local manifest and final test exist, every class is `pending` or
`not_testable`. A class with inadequate calibration remains `experimental` and
abstains. Results from contaminated/regression data are never external benchmark
claims.

Thresholding reduces forced answers but does not create an unknown-class model.
Raw softmax/detection values remain `model_score`, not calibrated probability.

## Safe next step

When the image is unclear, retake it using the mode-specific instructions. When a
symptom/pest matters operationally, preserve the observation and consult a local
PPL or qualified agronomy expert for field inspection. Expert review is still
required before Indonesian common names and guidance are frozen.

