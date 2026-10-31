# PPL/agronomy terminology and guidance review

Status: **pending expert review**. Do not mark approved without reviewer role, date,
and the exact UI/API text version. Keep reviewer identity/contact in private team
records; the tracked file may use an authorized reviewer code and professional role.

## Review record

- Reviewer code: __________________
- Professional role/organization type: __________________
- Relevant rice/agronomy experience: __________________
- Review date: __________________
- UI/API commit or release: __________________
- Outcome: [ ] approved  [ ] approved with changes  [ ] not approved

## Disease labels

| Model class | Proposed Indonesian display | Approved wording/change | Status |
| --- | --- | --- | --- |
| `bacterial_leaf_blight` | Hawar daun bakteri (kresek) |  | pending |
| `blast` | Blas |  | pending |
| `brown_spot` | Bercak cokelat |  | pending |
| `healthy` | Tidak ada gejala penyakit target yang dikenali pada foto ini |  | pending |
| `tungro` | Tungro |  | pending |

Confirm that everyday names are regionally understandable and do not collapse
distinct conditions. In particular, Narrow Brown Spot must not become Brown Spot.

## Pest labels

| Source index/class | Proposed Indonesian display | Approved wording/change | Status |
| --- | --- | --- | --- |
| 0 `rice leaf roller` | Hama putih palsu / penggulung daun padi |  | pending |
| 4 `yellow rice borer` | Penggerek batang padi kuning |  | pending |
| 7 `brown plant hopper` | Wereng batang cokelat |  | pending |

Confirm whether slash-separated alternatives help or confuse Lampung users, and
whether life-stage wording is needed. The UI detects visible insects, not damage or
hidden infestation.

## Required sentence-level checks

For every sentence, record approve/change/reject and the replacement text:

- [ ] “Hasil ini adalah indikasi model, bukan diagnosis.”
- [ ] Disease photo instruction: one leaf, symptom visible, natural even light,
      in focus, avoid strong shadow.
- [ ] Pest photo instruction: insect must be visible, close and in focus.
- [ ] Healthy wording does not imply the crop is safe.
- [ ] No-pest wording does not imply pest absence or safety.
- [ ] Retake guidance is feasible for farmers using a phone.
- [ ] PPL referral is actionable and locally appropriate.
- [ ] Limitations cover unsupported diseases/pests, nutrient deficiency, hidden
      insects, and poor photos.
- [ ] No sentence recommends a pesticide product, dose, spray schedule, or treatment
      without field assessment and label/official guidance.

## Agronomic source check

Compare wording with current Indonesian Ministry of Agriculture guidance and IRRI
diagnostic material, but treat the reviewer—not the model or an old handbook—as the
local terminology authority. Record source edition/date/URL consulted and any
regional difference.

## Unresolved items

| Item | Risk if unresolved | Owner | Due date | Resolution |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

Approval applies only to the recorded version. New class labels, guidance, or
next-action text require another review entry.

