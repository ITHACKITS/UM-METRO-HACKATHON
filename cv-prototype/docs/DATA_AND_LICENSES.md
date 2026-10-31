# Data sources, roles, and rights

This register states what each source is allowed to do in this project. A source's
availability on the internet is not permission to redistribute it.

| Source | Declared terms | Allowed role here | Prohibited/important boundary |
| --- | --- | --- | --- |
| `sharmin3/Rice-Leaf-Disease` | no declared dataset licence found | training-lineage documentation only | do not download, redistribute, or score as a project test set |
| Mendeley `fwcj7stb8r` | CC BY 4.0 | smoke/regression checks with attribution | class counts nearly reproduce training data; never claim external generalization |
| Mendeley `sjkptpgv79` | CC BY 4.0 | external field audit for exact Blast, Tungro, Healthy matches | Narrow Brown Spot is not Brown Spot; Sheath Blight is unsupported/OOD |
| Paddy Doctor | paper/repository/Kaggle terms differ by artifact | future secondary benchmark research | confirm the exact image source and applicable terms before download/use |
| IP102 | free for academic use according to source repository | pest lineage and academic evaluation | do not redistribute images or claim commercial clearance |
| Local Lampung photos | written owner consent plus expert review | decisive field audit | raw photos, identities, signatures, exact coordinates, and consent documents stay out of Git |
| Roboflow `capstone-aedws/rice-pest-jmdev`, CC BY 4.0 | hosted pest detector lineage | runtime fallback only with explicit per-request consent; published metrics are not TUAI accuracy | sends the submitted pest photo to an external service; only two semantically compatible classes are mapped |

## Frozen model artifacts

| Model | Revision | Repository licence statement | Project caveat |
| --- | --- | --- | --- |
| `Huyt/rice-leaf-disease-efficientnet-b0` | `a12e09fd765eda2b846836a965e951151a9125f7` | Apache-2.0 | training-dataset licence is not stated on the card; verify before commercial use |
| `underdogquality/yolo11s-pest-detection` | `b64a9302e50ae089e52b770fe0d054ac77c1c3d8` | MIT stated by third-party repository; upstream Ultralytics terms conflict/require clarification | IP102 academic-use lineage and Ultralytics licensing are downstream/commercial blockers |

The tracked model lock is authoritative for URLs, revisions, expected files,
hashes, label order, preprocessing, and conversion. Model weights are not committed.

### Unresolved Ultralytics licence conflict

The third-party pest repository labels its artifact MIT, while the current
[official Ultralytics licence page](https://www.ultralytics.com/license) states that
Ultralytics YOLO code/models use AGPL-3.0 by default and offers Enterprise terms for
proprietary/commercial deployment. Converting the checkpoint to ONNX in a separate
environment does not by itself resolve the provenance or obligations of the source
model. This documentation makes no legal conclusion: commercial/distributed use is
blocked pending written licensor/legal clarification, compliance with applicable
terms, or replacement with a detector trained from clearly licensed data and code.

## Local collection rules

1. Obtain written, voluntary consent before capture or use.
2. Assign a non-identifying image and group ID; keep the re-identification key and
   consent form in restricted team storage outside Git.
3. Remove EXIF and precise location from evaluation copies.
4. Record only coarse location when scientifically necessary and consented.
5. Group the same plant/insect/visit/burst before partitioning.
6. Have labels and pest boxes reviewed by a PPL/agronomist; record role/date without
   publishing personal contact details.
7. Delete or retain source data according to the consent choice and team policy.

## Possible public conversion fixtures

The following Wikimedia Commons files may be considered only for decoder/format or
box-overlay smoke tests after rechecking the live file page and attribution. They
are not Lampung evidence and must not enter a performance claim:

| Commons filename | Stated licence/credit | Narrow role |
| --- | --- | --- |
| `Rice Leafroller (Cnaphalocrocis medinalis) Crambidae (5828725363).jpg` | CC0 | rice-leaf-roller conversion/overlay fixture |
| `Rice yellow stem borer.jpg` | CC BY-SA 4.0, Md.Farhan Nabil | yellow-borer conversion/overlay fixture; preserve attribution and share-alike obligations |
| `Nilaparvata lugens - Brown planthopper - UGA5190055.jpg` | CC BY 3.0 US, Natasha Wright/Bugwood | brown-planthopper conversion/overlay fixture; preserve attribution |

Do not download these automatically. A fixture registry must record the exact file
page, original URL, retrieval date, SHA-256, author, licence version, changes, and
required notice. A species photograph is not an independent field-validation set.

## Required attribution fields

Every external manifest record includes source dataset ID, source key, original
label, canonical label, rights basis, redistribution permission, and content hash.
Any distributed aggregate report must cite the dataset and licence. It must not
include source images unless redistribution is explicitly permitted and necessary.

## Commercialization roadmap

The current models are technical prototypes, not commercially cleared assets. A
commercial path requires resolution or replacement of the Ultralytics/IP102 pest
lineage, plus a consented, locally representative dataset with explicit
training/deployment rights, expert labels, retraining or replacement under clear
terms, independent evaluation, and legal review of every upstream component.

