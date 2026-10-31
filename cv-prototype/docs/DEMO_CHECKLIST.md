# Demo and offline preflight checklist

Run the complete checklist on the actual demo laptop by 26 November 2026. Record
times, hashes, and failures in a dated private log; never tick an item from memory.

## Artifacts and provenance

- [ ] Disease revision is exactly `170d10e070c308e0e5337690d67371825591f35b`.
- [ ] Pest source revision is exactly `b64a9302e50ae089e52b770fe0d054ac77c1c3d8`.
- [ ] Every required model artifact matches the tracked SHA-256 lock.
- [ ] Runtime contains the pest ONNX; no `.pt`/pickle checkpoint is present.
- [ ] Model/cache size and free disk space are recorded.
- [ ] Threshold hash matches the frozen calibration report, or the UI explicitly
      shows calibration unavailable/experimental.
- [ ] Third-party notices and dataset roles match the final lockfiles/artifacts.

## Offline startup

- [ ] Disconnect Wi-Fi/Ethernet before starting.
- [ ] Canonical API starts on port 8000 without a download attempt.
- [ ] Root UI starts on port 5173 and `/sigap` loads from the phone browser.
- [ ] `/api/sigap/v1/health` reports both exact revisions and readiness.
- [ ] Prewarm both models, then record warm request p50/p95 and peak memory.
- [ ] Restart once from cold state to confirm repeatability.
- [ ] Confirm the optional Roboflow fallback is disabled for the offline rehearsal;
      the normal demo must not depend on a cloud credential or network availability.

## Optional hosted-fallback rehearsal

- [ ] Use only a newly rotated key supplied through `ROBOFLOW_API_KEY`; never copy it
      into source, frontend configuration, screenshots, logs, or presentation files.
- [ ] Confirm pest analysis does not contact Roboflow unless the server fallback is
      enabled and the user explicitly checks the per-request consent control.
- [ ] Confirm the result says it was processed by Roboflow cloud and the health response
      reports `offline=false` while the fallback is enabled.
- [ ] Confirm only brown planthopper and leaf folder are exposed; generic stem borer and
      every other hosted class are ignored.
- [ ] Disconnect the network and confirm hosted failure is explicit, while local disease
      inference remains usable and no fake pest result appears.

## User flow

- [ ] A 360 px phone viewport shows both modes without horizontal overflow.
- [ ] Disease mode explains one symptomatic leaf, close-up, even natural light.
- [ ] Pest mode asks for a visible insect and warns hidden pests are not inferred.
- [ ] Camera capture and gallery selection work.
- [ ] Preview, cancel, replace, loading, and backend-unavailable states work.
- [ ] Disease result says `indikasi model`, shows alternatives and model scores.
- [ ] Pest boxes align with the EXIF-normalized preview.
- [ ] Empty pest result does not say the plant is safe.
- [ ] Healthy output says no target symptom was recognized in this photo.
- [ ] Result shows revision/hash, limitations, and safe next action/PPL referral.
- [ ] There is no pesticide product, dose, or autonomous treatment instruction.

## Failure cases

- [ ] Corrupt, MIME-spoofed, unsupported, and decompression-bomb inputs fail safely.
- [ ] 12 MiB compressed and 25 MP decoded limits are verified at boundaries.
- [ ] Disease under 224 px and pest under 480 px request a retake.
- [ ] Blur/overexposure/underexposure warnings are understandable.
- [ ] Missing model produces a readiness/service error, never a fake prediction.
- [ ] Slow inference, two simultaneous requests, and user cancellation are tested.
- [ ] No uploaded bytes/image persists after response completion.
- [ ] Browser console has zero errors during the full flow.

## Evidence and privacy

- [ ] Demo photos are licensed, team-owned with consent, or clearly synthetic.
- [ ] A PPL/agronomist has reviewed Indonesian names and every guidance sentence.
- [ ] Claims link to immutable manifest/model/threshold hashes and aggregate report.
- [ ] Untested classes are visibly `not_testable`; model-card accuracy is absent.
- [ ] No raw private photo, exact location, consent record, or participant identity is
      present in Git or the demo browser cache/history.
- [ ] Boundary guard passes before staging/commit.

## Backup and presentation

- [ ] Record a 3–5 minute backup video using approved images.
- [ ] Show both modes, one honest abstention/retake, limitations, and offline status.
- [ ] Store one local copy and one access-controlled backup; test playback/audio.
- [ ] Pitch clearly separates visual observation from weather suitability.
- [ ] TKT claim matches evidence: TKT 4 only with representative integrated/user
      validation; otherwise TKT 3.
- [ ] A static screenshot/aggregate report is ready if inference hardware fails.

