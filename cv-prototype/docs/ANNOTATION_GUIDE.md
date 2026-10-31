# Annotation guide

## Roles

- Collector assigns non-identifying IDs and records consent/metadata separately.
- Primary annotator labels visible evidence without seeing model output.
- PPL/agronomist reviews terminology, class, and pest boxes.
- Adjudicator resolves documented disagreements; unresolved cases remain excluded
  from supported-class scoring or enter an explicit uncertain/OOD category.

Do not let the model's prediction become the ground truth.

## Grouping before labels or splitting

One leaf, insect, plant, field visit, or camera burst receives one `group_id`.
Derived rotations/compressions retain that group. Only after grouping, exact
hashing, and near-duplicate review may groups be assigned to calibration/test.

## Disease images

Capture a close, in-focus rice leaf in natural, even light. Retain realistic
background; do not crop so tightly that the expert loses context. Record:

- original expert wording;
- canonical label only when it is an exact approved match;
- plant part, crop age/variety if known, session, device family, coarse location;
- whether one or multiple conditions are visible;
- label reviewer role/date.

Canonical supported labels are `bacterial_leaf_blight`, `blast`, `brown_spot`,
`healthy`, and `tungro`. The model's `healthy` output is represented in copy as
`no_target_symptom_recognized`; ground-truth healthy still requires expert review.

Do not map Narrow Brown Spot to Brown Spot. Treat Sheath Blight, nutrient deficiency,
chemical injury, uncertain/mixed symptoms, and non-rice images as unsupported/OOD
unless the expert provides a separate documented category.

## Pest images and boxes

Supported canonical labels:

- source index 0 `rice_leaf_roller`;
- source index 4 `yellow_rice_borer`;
- source index 7 `brown_plant_hopper`.

Draw one tight box around each **visible insect instance**, including visible body
parts but excluding large areas of plant/background. Do not draw boxes around
damage alone, rolled leaves without a visible pest, eggs/larvae that the taxonomy
does not clearly support, or an inferred hidden borer. Mark truncation, heavy
occlusion, life stage, and ambiguity in the private annotation tool when possible.

Coordinates in the manifest are normalized to the EXIF-corrected width/height:
`x_min`, `y_min`, `x_max`, `y_max` in `[0,1]`, with minimums below maximums. A second
reviewer verifies class and box. Negative images need a recorded inspection; an
empty annotation file alone is not an authoritative absence label.

## Quality and OOD labels

Keep representative failures: blur, poor exposure, occlusion, clutter, multiple
leaves/insects, non-rice subjects, screenshots, blank/corrupt files, and unsupported
conditions. Do not remove difficult photos merely because the model fails on them.

## Privacy and file handling

Never place raw local images, precise coordinates, names, phone numbers, signatures,
consent scans, or a participant re-identification key in Git. Strip EXIF from
evaluation copies. Use only the content hash and non-identifying source key in the
tracked/frozen manifest.

## Review checklist

- [ ] Consent/rights basis is recorded off-Git.
- [ ] Image and group IDs contain no identity/location.
- [ ] SHA-256 and perceptual hash were calculated before splitting.
- [ ] Canonical mapping is exact and documented.
- [ ] Annotator did not see the model prediction.
- [ ] Pest boxes are instance-level and expert-reviewed.
- [ ] Conflicts/uncertainty are retained, not silently relabelled.
- [ ] Same group never crosses calibration/final-test partitions.

