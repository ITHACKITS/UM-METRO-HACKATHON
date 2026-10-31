<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/public/logo/tuai-lockup-dark.svg" />
    <img src="frontend/public/logo/tuai-lockup.svg" alt="TUAI" width="240" />
  </picture>
</p>

<p align="center"><b>Sistem pertanian cerdas berbasis citra satelit dan computer vision.</b><br/>
Monitoring kondisi padi, deteksi penyakit dan hama, giliran air, dan prediksi hasil panen dalam satu peta per blok sawah.<br/>
<i>"Tuai" berarti memanen padi.</i></p>

<p align="center">Tim Infinits · <b>UM Metro Hackathon 2026</b>, sub tema A · Metro, Lampung · <a href="README.md">English</a></p>

![Halaman depan TUAI: diorama lanskap sawah di dalam balok air, dengan petani, kuntul, kerbau dan ikan](docs/screenshots/landing-hero.png)

> [!WARNING]
> TUAI adalah alat perkiraan ilmiah, **bukan sistem peringatan resmi**. Untuk keputusan, ikuti BMKG, penyuluh pertanian (PPL) dan BPBD.

## Masalah

Petani dan P3A tidak tahu sejak awal kapan dan di blok mana sawahnya berisiko, sehingga tindakan datang terlambat.

| Fokus | Kenapa terlambat atau sulit |
|---|---|
| Kekeringan | Kurang air baru terlihat saat daun menggulung. Giliran air dibagi tanpa data kebutuhan tiap blok. |
| Genangan | Padi biasa rusak jika terendam penuh sekitar 5 hari. Tidak ada peta blok mana yang tergenang dan sudah berapa lama. |
| Penyakit | Gejala blas, kresek dan tungro mirip bagi mata awam. |
| Hama | Wereng coklat kecil dan hidup di pangkal batang; penggerek batang baru ketahuan dari sundep atau beluk. Hama dan penyakit tertukar, obat yang disemprot bisa salah. |
| Hasil panen | Hasil baru diketahui saat panen, sehingga sulit merencanakan penjualan, simpanan atau modal musim berikutnya. |

Data nasional padi 2024 (Pusdatin Kementan, *Statistik Iklim, OPT dan DPI 2024*, s.d. 11 Okt 2024): banjir 172.093 ha (puso 50.142 ha), kekeringan 134.440 ha (22.674 ha), penggerek batang 61.711 ha, blas/kresek/tungro 46.826 ha, tikus 46.023 ha (puso 1.205 ha), WBC 27.058 ha. Di Lampung, serangan WBC naik hampir 6 kali dan penggerek batang hampir 2 kali dalam dua tahun. Kenaikan serangan hama adalah faktor terkuat penurunan hasil padi sawah, peluang 9,43 kali ([Prasetyo & Kadir 2023](https://mpra.ub.uni-muenchen.de/119446/), 50.619 petak ubinan).

Wawancara mitra (petani sejak 1980-an, 3 ha, irigasi): gagal panen karena tikus, wereng dan kekeringan; *"Gagal panen gaada tanda-tandanya"*; panen normal 6 ton/ha, saat gagal hanya 3 kuintal/ha; tidak ada kabar dari pemerintah atau BMKG.

## Ringkasan

TUAI menampilkan semua informasi dalam **satu peta per blok sawah dengan warna hijau, kuning atau merah, lengkap dengan saran tindakan**. Dua sumber data saling melengkapi: **satelit** memantau seluruh hamparan tanpa datang ke sawah (kehijauan, kadar air tanaman, genangan), dan **foto dari kamera HP** menangkap yang tidak terlihat satelit (penyakit di daun, hama di pangkal batang).

| Fitur | Fokus challenge | Yang dikerjakan | Di mana |
|---|---|---|---|
| **TUAI Pantau** | Monitoring kondisi tanaman | NDVI dan NDMI per blok dari Sentinel-2 dibanding lahan sekitar, fase tumbuh dari tanggal tanam | Halaman lahan, setiap blok |
| **TUAI Siaga** | Monitoring kondisi tanaman | Prakiraan hujan BMKG dan peta genangan radar Sentinel-1 (deteksi perubahan ala UN-SPIDER): peringatan hujan lebat, blok tergenang, lama terendam | Halaman lahan, tab banjir |
| **TUAI Sigap** | Deteksi penyakit dan hama | Foto → AI: 5 kelas daun (kresek, blas, bercak coklat, tungro, sehat), hitung wereng YOLO, model gejala hama; laporan cepat tikus; cek PPL; peta sebaran desa dan peringatan blok sekitar | `/sigap` |
| **TUAI Lancar** | Rekomendasi untuk petani | Kebutuhan air FAO-56 tiap blok dicek dengan Pantau: merah/kuning/hijau dan urutan giliran air untuk ketua P3A, blok berbunga lebih dulu; catatan keputusan per musim | `/ppl` → Giliran air |
| **TUAI Taksir** | Prediksi hasil panen | Musim pertama: di bawah/sekitar/di atas rata-rata blok dari NDVI/NDMI fase berbunga–pengisian bulir dan catatan kejadian; setelah dua musim hasil timbang, regresi linear dalam t/ha beserta rentang | `/ppl` → Taksir panen |

## Fitur

| Fitur | Isi |
|---|---|
| TUAI Sigap: cek foto | `/sigap`: foto daun, pangkal rumpun atau gejala lain. Model daun mengenali kresek, blas, bercak coklat, tungro atau sehat; detektor YOLO memberi kotak dan menghitung wereng; model gejala mengenali penggerek batang, hispa atau pelipat daun. Di bawah keyakinan 70% atau bila model berbeda pendapat, hasil ditandai *perlu dicek* dan diteruskan ke PPL. Saran awal hanya pengamatan dan cara budidaya, ditandai draf sampai dicek PPL. |
| TUAI Sigap: laporan dan peta desa | Hasil foto dan laporan cepat tikus (lokasi, tingkat kerusakan) masuk antrean PPL (benar, ganti label, tolak; PIN opsional). Laporan terverifikasi jadi titik di peta desa; dua laporan wereng atau tikus terverifikasi dalam 500 m selama seminggu memberi peringatan ke blok sekitar (angka bisa diatur, diuji saat pilot). |
| TUAI Lancar: giliran air | `/ppl` → Giliran air: ketua P3A mengisi tanggal tanam, varietas dan jenis tanah tiap blok (atau SoilGrids mengisi tanah). Tiap blok mendapat kebutuhan air FAO-56 7 hari dalam mm dan m³; merah bila hitungan air dan Pantau sama-sama buruk, kuning bila hanya satu (cek ke sawah), blok merah yang berbunga lebih dulu. Keputusan dan hasilnya dicatat per musim. |
| TUAI Taksir: perkiraan panen | `/ppl` → Taksir panen: kelas dibanding rata-rata blok di musim pertama; ton/ha beserta rentang setelah 8 hasil timbang dari 2 musim tercatat. |
| TUAI Siaga | Prakiraan resmi BMKG 3 hari untuk desa terdekat dengan peringatan hujan lebat (≥ 50 mm/hari), deteksi genangan radar dengan lama terendam, dan prakiraan terendam dari neraca air. Peringatan Siaga tinggi menaikkan status aman menjadi *Waspada*. |
| Tampilan Petani | Layar utama: status **Aman / Waspada / Bahaya**, alasannya dalam satu kalimat, dan satu hal yang dikerjakan hari ini. Grafik ada di tampilan **Ahli**. |
| Peringatan Telegram | Sekali tekan, sawah terhubung ke Telegram. Tiap pagi (06.00 WIB) bot mengirim pesan selama sawah berisiko, dan sekali lagi saat kembali aman. `/cek` dan `/stop`. |
| Dasbor P3A & PPL | `/ppl`: semua petak binaan di satu peta, diwarnai dan diurutkan menurut risiko. Impor/ekspor batas petak GeoJSON. |
| Gambar lahan | Ketuk sudut petak di citra Esri atau Sentinel-2 cloudless. |
| Kering | Hari mulai stres air (P5/P50/P95), peluang harian, alasan, langkah (AWD, tambal pematang, pompa, mulsa, giliran air P3A). |
| Banjir | Tinggi genangan vs tinggi tanaman, hari terendam penuh, ensemble debit GloFAS, tinggi lahan di atas saluran, air dari radar Sentinel-1. |
| Hama | Blas, hawar daun bakteri, wereng cokelat, penggerek batang; cara mengecek, tanpa dosis pestisida. |
| Sumber air | Sungai, saluran, embung, sumur dari OpenStreetMap beserta jaraknya. |
| Uji skenario | Ubah hujan, tunda hujan, pemanasan, hujan ekstrem, irigasi; hasil diberi cap **hipotetis**. |
| Pemutar hari | 30 hari, warna lahan berubah sesuai stres atau kedalaman air, strip risiko harian. |
| Si Padi | Menjawab hanya dari data lahan, menyebut sumber, jujur kalau data tidak ada. Bisa memakai Claude atau Google Gemini (`LLM_PROVIDER=anthropic` atau `gemini`); tanpa kunci API, menjawab dengan templat. |
| Laporan | A4 berisi peta, gauge, grafik, langkah, hama, sumber air, sumber data, kolom tanda tangan PPL. |
| Mode luring | `JAGAPADI_OFFLINE=1` memutar ulang respons asli yang direkam. |
| IoT | `POST /api/sensors/{lahan}` untuk sensor ESP32; contoh firmware di `scripts/firmware`. |

<table>
  <tr>
    <td align="center" width="50%"><img src="docs/screenshots/app-petani.png" alt="Tampilan Petani: satu status, satu alasan, satu langkah" /><br/><sub>Tampilan Petani: satu status, satu alasan, satu langkah</sub></td>
    <td align="center" width="50%"><img src="docs/screenshots/ppl-dashboard.png" alt="Dasbor P3A dan PPL: blok diurutkan menurut risiko" /><br/><sub>Dasbor P3A dan PPL: blok diurutkan menurut risiko</sub></td>
  </tr>
  <tr>
    <td align="center" width="50%"><img src="docs/screenshots/app-sigap.png" alt="TUAI Sigap: foto daun terbaca blas" /><br/><sub>TUAI Sigap: foto daun → blas 83%, saran awal, laporan ke PPL</sub></td>
    <td align="center" width="50%"><img src="docs/screenshots/app-lancar.png" alt="TUAI Lancar: urutan giliran air" /><br/><sub>TUAI Lancar: urutan giliran air per blok</sub></td>
  </tr>
</table>

Tangkapan layar lain ada di [README bahasa Inggris](README.md#screens).

## Coba dalam tiga langkah

1. Buka aplikasi, tekan **Buka peta**.
2. Tekan **Pakai lahan contoh** atau **Gambar lahan**.
3. Baca status dan langkah hari ini. Tekan **Kirim peringatan ke Telegram**, atau **Lihat detail lengkap** untuk grafik, uji skenario dan Si Padi.

Untuk kelompok tani: buka **Dasbor P3A & PPL** (`/ppl`) lalu **Pakai contoh kelompok tani**. Buka **Data blok** untuk mengisi tanggal tanam, varietas dan tanah, lalu pakai tab **Giliran air** (Lancar) dan **Taksir panen**.

Untuk hama dan penyakit: buka **TUAI Sigap** (`/sigap`), foto tanaman, pilih petak, kirim laporan; PPL memeriksanya di **Cek PPL**.

Model foto Sigap (opsional, sekitar 2 GB dengan PyTorch): `pip install -r backend/requirements-ml.txt`.

## Menjalankan secara lokal

```bash
npm run setup
npm run dev        # API :8000, web :5173
# atau
docker compose up --build   # http://localhost:8000
```

Variabel konfigurasi ada di `backend/.env.example`; semuanya opsional. Peringatan Telegram aktif kalau `TELEGRAM_BOT_TOKEN` diisi (buat bot lewat @BotFather). Chatbot Si Padi memakai Gemini kalau `LLM_PROVIDER=gemini` dan `LLM_API_KEY` berisi kunci dari aistudio.google.com.

Deploy: repo ini adalah Blueprint [Render](https://render.com) (`render.yaml`). Lihat [Deploy](README.md#deploy).

## Metode, validasi dan keterbatasan

Lihat bagian [Scientific method](README.md#scientific-method) dan [Validation and limitations](README.md#validation-and-limitations). Singkatnya: neraca air FAO-56 per anggota ensemble, SCS-CN untuk limpasan, Gumbel untuk banjir 2-tahunan, pembacaan Sentinel-2 tanpa model terlatih. Uji konsistensi neraca air vs kelembapan tanah model Open-Meteo: r = 0,095, MAE = 0,037 m³/m³ (model vs model, bukan data lapangan). Uji mundur kemarau 2005-2025: hari stres air sejalan dengan El Niño (korelasi peringkat ONI 0.64) dan IOD positif (DMI 0.74), AUC 0.95. Tetapi total hujan kemarau saja memberi skor yang sama, dan tahun 2023 tidak menonjol di titik ini. Akurasi per petak **belum dapat diuji** karena tidak ada catatan lapangan.

## Kesesuaian dengan konsep

Yang ditulis di *Konsep TUAI Tim Infinits*, dan di mana prototipe sengaja berbeda.

| Lapisan | Konsep | Prototipe | Alasan |
|---|---|---|---|
| Olah citra satelit | Google Earth Engine (Python API) | COG Sentinel-2 L2A dari Earth Search dan Sentinel-1 RTC dari Planetary Computer, dibaca langsung | Tanpa akun atau lisensi, bisa luring dari rekaman; GEE perlu lisensi berbayar untuk komersial |
| Masker awan | Cloud Score+ | Kelas SCL Sentinel-2 | Cloud Score+ adalah koleksi GEE |
| Masker air permanen, lereng | JRC Global Surface Water, HydroSHEDS | Perbandingan cincin lahan sekitar, lereng dari Copernicus DEM GLO-90 (aturan 5% UN-SPIDER) | Tujuan sama tanpa GEE; JRC masih perlu ditambah |
| Cuaca | BMKG + Open-Meteo | Prakiraan 3 hari BMKG (kode desa terdekat) + Open-Meteo / ensemble ECMWF | Sesuai rencana |
| Penyakit daun | Hugging Face Transformers | `prithivMLmods/Rice-Leaf-Disease`, revisi dikunci | Sesuai rencana; wajib diuji ulang dengan foto lapangan |
| Deteksi hama | PyTorch + Ultralytics YOLO | `backend/models/wereng.pt` lokal atau model Roboflow | Bobot dilatih dengan `scripts/sigap/train_wereng.py`; tidak ikut repo |
| Prediksi panen | scikit-learn | scikit-learn `LinearRegression` | Sesuai rencana |
| Basis data blok | PostgreSQL + PostGIS | Berkas JSON di `backend/data/{sigap,lancar,taksir}` dan blok di peramban (impor/ekspor GeoJSON) | Cukup untuk pilot dua mitra; PostGIS saat blok dipakai bersama banyak perangkat |
| Tampilan | Website PWA (React) + Leaflet | React + MapLibre GL | MapLibre sudah terpasang; belum bisa dipasang sebagai PWA |

## Tim

Tim Infinits, Program Studi Teknologi Informasi, Institut Teknologi Sepuluh Nopember:

- M. Hikari Reiziq Rakhmadinta: ketua tim, bisnis dan hilirisasi
- Ahmad Wildan Fawwaz: operasional, regulasi dan penyusun proposal
- Muhammad Rakha Hananditya Rauf: kecerdasan buatan (model Sigap, Pantau, Siaga, Taksir)
- Arya Bisma Putra Refman: website, backend, peta blok, hitungan air (Lancar), API cuaca
- Muhammad Ziddan Habibi: validasi pengguna dan penghubung mitra
- Dosen pendamping: Prof. Dr. Dedin Finatsiyatull Rosida, STP, MKes

## Lisensi

Kode MIT. Maskot milik tim. Atribusi data dan pustaka: [CREDITS.md](CREDITS.md).
