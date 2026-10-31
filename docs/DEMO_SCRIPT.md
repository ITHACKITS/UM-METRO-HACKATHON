# 3-minute demo script

Demo Day MVP per the concept paper: TUAI Sigap, TUAI Lancar and the partner's block map.

Before the demo:
- Run the app once on the sample field and the sample farmer group (fills the caches). If venue Wi-Fi is doubtful, start the API with `JAGAPADI_OFFLINE=1`; recordings are real and show their capture time.
- On `/ppl`, open **Data blok** for each sample plot and fill in a transplanting date and variety, so Lancar shows real growth stages.
- Install `backend/requirements-ml.txt` and send one photo through `/sigap` beforehand, so the leaf model is downloaded and loaded.
- Have one clear photo of a diseased rice leaf on the phone or laptop. Do not demo with non-leaf images: the model is overconfident on them.

**0:00 – Problem (25 s).** Landing page. "In 2024, floods hit 172 thousand hectares of rice, and in Lampung brown planthopper attacks rose almost six-fold in two years. Our partner, farming since the 1980s, said: crop failure comes without warning." Click **Kering** and **Banjir** on the dock, back to **Normal**.

**0:25 – TUAI Pantau and Siaga (25 s).** **Buka peta** → **Pakai lahan contoh**. The farmer view: one status, one reason, one action. **Ahli** → **Banjir** tab: the TUAI Siaga card with BMKG's 3-day forecast for the nearest village and the Sentinel-1 radar reading. "Satellite watches the whole area without a field visit."

**0:50 – TUAI Sigap (50 s).** **TUAI Sigap** → **Daun** → take or pick the leaf photo. The result: disease name, confidence, *perlu dicek PPL* or not, first advice marked as draft. "The system never just says spray." Tap the plot on the map, **Kirim laporan**. Switch to **Cek PPL**: the report waits there; press **Benar**. "Checked reports become the village pest map; two planthopper or rat reports nearby in a week warn the blocks around them." Show **Lapor tikus**: "Rats are not in any photo dataset, so they get a quick form; they caused the largest crop loss among rice pests in 2024."

**1:40 – TUAI Lancar (40 s).** **Dasbor P3A & PPL** → **Giliran air** → **Hitung urutan giliran air**. "Each block's water need for the next 7 days from FAO-56, checked against the satellite. Red means both say dry; yellow means check the field. Flowering blocks go first." Point at the map colours, then the decision log: "the P3A chair records what was decided, so each season has a record."

**2:20 – TUAI Taksir and honesty (40 s).** **Taksir panen** → run. "Season one gives below, around or above the block average; tonnes per hectare come after two seasons of weighed harvests from our partners." README, Concept alignment and Validation: "What we have not validated, we say: the planthopper detector still needs training, and the leaf model must be retested on field photos in the pilot from December."
