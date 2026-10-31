# TUAI Sigap evaluation toolkit

This directory contains the reproducible, aggregate-only evaluation workflow for
the computer-vision prototype. It does **not** contain photographs, consent
records, names, precise locations, or claimed results.

The workflow deliberately separates four states:

- `pending`: the required evidence has not been supplied yet;
- `not_testable`: too few independent examples exist for a defensible metric;
- `experimental`: evidence exists, but the acceptance rule was not met;
- `tested`: a frozen manifest and independent final-test results exist.

Until the team freezes a consented, expert-labelled manifest, the report command
emits `pending`/`not_testable`. It never substitutes model-card accuracy.

## Local use

Python 3.12 or newer is recommended. From this directory:

```bash
python -m unittest discover -s tests -v
python -m jagapadi_eval validate examples/manifest.synthetic.json
python -m jagapadi_eval audit-manifest examples/manifest.synthetic.json
python -m jagapadi_eval report examples/manifest.synthetic.json --output /tmp/jagapadi-report.md
```

The example is synthetic metadata, not a benchmark. Image hashing is performed
against a private local folder and only its non-identifying hashes belong in a
frozen manifest:

```bash
python -m jagapadi_eval hash-image /private/path/example.jpg
```

Do not add private image paths or raw images to Git.

Threshold selection accepts a private JSON export from the grouped calibration
partition and prints deterministic JSON to standard output:

```bash
python -m jagapadi_eval calibrate-disease /private/calibration-disease.json
python -m jagapadi_eval calibrate-pest /private/calibration-pest.json
```

Disease input contains `classes`, `samples` (`true_label`, `predicted_label`,
`score`, `margin`), and optional policy limits. Pest input contains `classes`,
already one-to-one-matched `detections` (`class_name`, `score`,
`is_true_positive`), and `ground_truth_counts`. Defaults require 20 calibration
examples/instances, at most 10% disease selective error, and at least 85% pest
precision. Save and hash the output before final testing.

