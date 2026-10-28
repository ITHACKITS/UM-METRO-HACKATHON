<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/public/logo/jagapadi-lockup-dark.svg" />
    <img src="frontend/public/logo/jagapadi-lockup.svg" alt="Jagapadi" width="300" />
  </picture>
</p>

<p align="center"><b>Jaga sawah sebelum kering atau banjir.</b><br/>
Citra satelit, cuaca dan ketinggian lahan diolah menjadi prakiraan dua minggu dan rencana kerja untuk satu petak sawah.</p>

<p align="center">Dibuat untuk <b>[NAMA HACKATHON]</b> · Metro, Lampung · <a href="README.md">English</a></p>

![Halaman depan Jagapadi: diorama lanskap sawah di dalam balok air](docs/screenshots/landing-hero.png)

> [!WARNING]
> Jagapadi adalah alat perkiraan ilmiah, **bukan sistem peringatan resmi**. Untuk keputusan, ikuti BMKG, penyuluh pertanian (PPL) dan BPBD.

## Masalah

Petani biasanya baru tahu sawahnya kekurangan air saat tanah sudah retak, dan baru tahu banjir saat petak sudah tergenang. Tandanya sudah terlihat lebih dulu di citra satelit, ensemble cuaca dan prakiraan debit sungai, tetapi data itu tidak sampai ke pematang.

- Luas panen padi 2023 sekitar 10,21 juta ha, **turun 2,29%** dari 2022 saat El Niño menguat ([BPS via Bisnis.com](https://ekonomi.bisnis.com/read/20240301/99/1745543/bps-luas-panen-padi-2023-merosot-229-sepanjang-2023)).
- Produksi beras 2023 31,10 juta ton, **turun sekitar 440 ribu ton** ([BPS via Kontan](https://nasional.kontan.co.id/news/produksi-beras-nasional-turun-440000-ton-pada-2023-bps-terdampak-el-nino)).
- Kemarau 2019: **102.746 ha** sawah terdampak kekeringan, **9.358 ha** puso ([Kementan via detikFinance](https://finance.detik.com/berita-ekonomi-bisnis/d-4616392/9-300-hektare-sawah-gagal-panen)).

## Ringkasan

Petani atau PPL menggambar petak di peta satelit. Jagapadi lalu membaca riwayat Sentinel-2 petak itu (NDVI, NDWI, air terbuka) dan membandingkannya dengan lahan sekitar, menjalankan neraca air sawah FAO-56 pada **51 skenario hujan ECMWF**, memeriksa debit sungai GloFAS terhadap banjir 2-tahunan, lalu memberi risiko kekeringan, banjir dan kesesuaian cuaca untuk hama, lengkap dengan alasan, langkah yang diurutkan dari paling mudah, sumber air terdekat, simulator skenario, chatbot Si Padi dan laporan A4.

Setiap angka berasal dari sumber terbuka atau dihitung darinya, dengan waktu pengambilannya. Kalau sumber gagal, aplikasi menyebut sumber mana dan alasannya.

## Fitur

| Fitur | Isi |
|---|---|
| Gambar lahan | Ketuk sudut petak di citra Esri atau Sentinel-2 cloudless. |
| Kering | Hari mulai stres air (P5/P50/P95), peluang harian, alasan, langkah (AWD, tambal pematang, pompa, mulsa, giliran air P3A). |
| Banjir | Tinggi genangan vs tinggi tanaman, hari terendam penuh, ensemble debit GloFAS, tinggi lahan di atas saluran. |
| Hama | Blas, hawar daun bakteri, wereng cokelat, penggerek batang; cara mengecek, tanpa dosis pestisida. |
| Sumber air | Sungai, saluran, embung, sumur dari OpenStreetMap beserta jaraknya. |
| Uji skenario | Ubah hujan, tunda hujan, pemanasan, hujan ekstrem, irigasi; hasil diberi cap **hipotetis**. |
| Pemutar hari | 30 hari, warna lahan berubah sesuai stres atau kedalaman air, strip risiko harian. |
| Si Padi | Menjawab hanya dari data lahan, menyebut sumber, jujur kalau data tidak ada. |
| Laporan | A4 berisi peta, gauge, grafik, langkah, hama, sumber air, sumber data, kolom tanda tangan PPL. |
| Mode luring | `JAGAPADI_OFFLINE=1` memutar ulang respons asli yang direkam. |
| IoT | `POST /api/sensors/{lahan}` untuk sensor ESP32; contoh firmware di `scripts/firmware`. |

## Coba dalam tiga langkah

1. Buka aplikasi, tekan **Buka peta**.
2. Tekan **Pakai lahan contoh** atau **Gambar lahan**.
3. Baca tab Ringkasan, Kering, Banjir, putar linimasa, coba **Uji skenario** atau tanya Si Padi.

## Menjalankan secara lokal

```bash
npm run setup
npm run dev        # API :8000, web :5173
# atau
docker compose up --build   # http://localhost:8000
```

Variabel konfigurasi ada di `backend/.env.example`; semuanya opsional.

## Metode, validasi dan keterbatasan

Lihat bagian [Scientific method](README.md#scientific-method) dan [Validation and limitations](README.md#validation-and-limitations). Singkatnya: neraca air FAO-56 per anggota ensemble, SCS-CN untuk limpasan, Gumbel untuk banjir 2-tahunan, pembacaan Sentinel-2 tanpa model terlatih. Uji konsistensi neraca air vs kelembapan tanah model Open-Meteo: r = 0,095, MAE = 0,037 m³/m³ (model vs model, bukan data lapangan). Akurasi kejadian kekeringan dan banjir **belum dapat diuji** karena tidak ada catatan lapangan.

## Tim

Hikari Reiziq · Ziddan Habibi · Aryarefman. Dosen pembimbing: menyusul.

## Lisensi

Kode MIT. Maskot milik tim. Atribusi data dan pustaka: [CREDITS.md](CREDITS.md).
