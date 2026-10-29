# 3-minute demo script

Before the demo: run the app once on the sample field and the sample farmer group (fills the caches). If venue Wi-Fi is doubtful, start the API with `JAGAPADI_OFFLINE=1`; the recorded responses are real and show their capture time. For the Telegram step, set `TELEGRAM_BOT_TOKEN` and have Telegram open on a phone.

**0:00 – Problem (25 s).** Landing page. "In 2023 El Niño cut Indonesia's rice harvest area by 2.29%. NOAA's index says another El Niño is building now, +2.16 in August. Farmers learn about drought when the soil cracks." Click **Kering** on the dock: the paddies dry and crack. Click **Banjir**: muddy water rises. Back to **Normal**.

**0:25 – One field, one answer (30 s).** **Buka peta** → **Pakai lahan contoh**. While it loads: "We read this field's Sentinel-2 history, Sentinel-1 radar through the clouds, 51 ECMWF rain scenarios, GloFAS river flow and the terrain." The farmer view appears: **BAHAYA**, "the field may run short of water around 6 Nov", and one thing to do today. "This is all a farmer needs to read."

**0:55 – It comes to the farmer (25 s).** **Kirim peringatan ke Telegram** → Start in Telegram. The first message arrives: status, reason, today's action. "Every morning while the field is at risk, and once when it is safe again. No app to install."

**1:20 – The extension officer (25 s).** **Dasbor penyuluh** → **Pakai contoh kelompok tani**: five real plots on one map, ranked by risk. "One officer advises hundreds of plots. Now they see which ones to visit first." **Buka analisis** on the top plot.

**1:45 – The science, for the judges (30 s).** **Ahli**: the first-stress day with its P5–P95 range, the daily probability strip, the drivers. **Uji skenario**: rain ×0.3 → run; the banner says HIPOTETIS. "Planning, not a forecast."

**2:15 – Honesty (30 s).** README, Validation: "We ran the model through 21 dry seasons. Its worst years are El Niño and Indian Ocean Dipole years, AUC 0.95. But a plain rain total does as well, and 2023 does not stand out at this grid point. We say that. Field-level skill needs records from a farmer group in Metro: that is our next step." **Cetak laporan** for the A4 report with every source and capture time.
