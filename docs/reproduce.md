# Merekonstruksi dataset dan evaluasi

**Status jujur:** panduan ini BELUM diuji end-to-end dari nol oleh orang lain. Langkah dan angka kontrol diambil dari kode dan dari `docs/experiment_design.md`, bukan dijalankan ulang untuk menulis dokumen ini. Perintah Docker untuk Nazario klasik adalah padanan dari perintah Nazario modern yang sudah dipakai.

## Baca dulu: keamanan data

- Korpus phishing berisi lampiran berbahaya sungguhan. File mbox Nazario TIDAK boleh diunduh ke komputermu. Ekstraksi hanya di dalam container Docker sekali pakai (`--rm`), dan hanya CSV teks bersih yang keluar.
- Jangan membuka email korpus di klien email atau browser, jangan mengunjungi tautannya, dan jangan mengirimnya ke sistem email sungguhan (penyusun SpamAssassin melarangnya).
- `data/raw`, `data/interim`, dan `data/processed` diabaikan Git. Periksa dengan `git check-ignore -v data/interim/x` sebelum mengunduh, dan jangan pernah meng-commit data.
- Pakai hanya container sekali pakai. Jangan menjalankan perintah pembersihan massal pada Docker milikmu.
- Lisensi, atribusi, dan alamat sumber (defanged: hxxps = https, [.] = titik) ada di `SOURCES.md` dan `NOTICE`. Pulihkan alamatnya sendiri.

## Persiapan

1. Python 3.14 (diuji 3.14.3) dalam venv, lalu `python -m pip install --only-binary=:all: -r requirements-analysis.txt`.
2. Docker, hanya untuk Nazario. Siapkan sekitar 100 MB unduhan dan memori Docker yang cukup (di sini 16,4 GB).
3. Jalankan semua perintah dari akar repo.

## Langkah rekonstruksi dan angka kontrol

1. **SpamAssassin (ham dan spam).** Unduh lima arsip set 20030228 dari direktori korpus (nama dan SHA256 di `SOURCES.md`). Ekstrak sehingga ada folder `data/interim/spamassassin/easy_ham`, `easy_ham_2`, `hard_ham`, `spam`, `spam_2` berisi berkas bernama 5 digit, titik, 32 karakter heksa. Cara ekstraksi arsip tidak dicatat di repo. Lalu jalankan `python -m src.extract_spamassassin`. Harapan: 6047 email dan gagal 0 di tiap subset.
2. **Nazario klasik (phishing, 5 file).** Perintah ini mengunduh ke memori container dan hanya menulis `nazario_clean.csv`. Git Bash di Windows:

   ```bash
   mkdir -p data/interim/nazario
   MSYS_NO_PATHCONV=1 docker run --rm -i -v "$(pwd -W)/src:/app/src:ro" -v "$(pwd -W)/data/interim/nazario:/out" -w /app python:3.12-slim python - < src/extract_nazario.py
   ```

   Di Linux atau macOS ganti `$(pwd -W)` dengan `$(pwd)` dan hapus `MSYS_NO_PATHCONV=1`. Harapan: 5010 email dan gagal 0.
3. **Nazario modern (HANYA uji, 11 file 2015 sampai 2025).** Sama seperti langkah 2 dengan folder `data/interim/nazario_modern` dan `src/extract_nazario_modern.py`. Skrip memeriksa ukuran tiap file (batas 40 MB) sebelum mengunduh dan berhenti bila ada yang gagal. Harapan: 3466 email, gagal 0, 84 `body_text` kosong.
4. `python -m src.build_dataset` menulis `data/processed/emails_all.csv`. Harapan: 11057 baris.
5. `python -m src.make_clean_dataset` menulis `data/processed/emails_clean.csv`. Harapan: tercetak `Total email: 9298 | total grup: 7271`.
6. **Pembagian data: JANGAN jalankan `src/make_splits.py`.** Pakai `docs/split_list.tsv` (hash, label, grup, bagian; tanpa isi email):

   ```bash
   python -c 'import pandas as pd; pd.read_csv("docs/split_list.tsv", sep="\t", keep_default_na=False).to_csv("data/processed/splits.csv", index=False)'
   ```

   Skrip hilir menggabungkan `splits.csv` dengan `emails_clean.csv` lewat `content_hash`, dan hasil gabungan harus 9298 baris tanpa baris kosong. Urutan baris berbeda dari berkas aslinya, jadi hash berkas `splits.csv` bukan pembanding yang berlaku.
7. **Sidik jari.** `python src/fingerprint_groups.py simpan` mencetak `baris` 9298, `n_grup` 7271, `sha_partisi` a0edd8587f0fcc56, dan `sha_urutan_baris` db9f05f620f0fe88. `sha_partisi` tidak peka penomoran ulang grup. `sha_urutan_baris` peka urutan baris, jadi perbedaan di situ saja bukan bukti kegagalan; perbedaan `sha_partisi` atau jumlah baris adalah tanda data sumber bergeser.
8. **MeAJOR (opsional, HANYA uji eksternal).** Unduh dari halaman Zenodo (di `SOURCES.md`, CC BY 4.0) dan simpan sebagai `data/raw/meajor_cleaned_preprocessed.parquet.gzip`. MD5 dan SHA256 ada di `SOURCES.md`. Hanya dibutuhkan oleh `python -m src.eval_meajor`.

## Jangan dijalankan ulang

- `src/make_splits.py`: menimpa pembagian data, dan hasilnya bisa berbeda antar versi library. Pakai daftar split.
- `src/freeze_model.py`: melatih ulang dan menulis ulang model beserta manifest, sehingga hash berubah dan semua rujukan hash rusak. Pakai zip dari Release.
- `src/eval_test_final.py`: test dibuka SEKALI sesuai aturan proyek. Skrip menolak jalan bila `data/processed/test_proba.csv` sudah ada, tetapi di mesin yang belum menjalankannya, ia akan membuka test. Jalankan hanya dengan sadar.
- `src/extract_nazario.py` dan `src/extract_nazario_modern.py` di luar Docker.

## Model dan evaluasi

- Model tidak dilatih ulang di panduan ini. Pasang dari Release v1.0.0 dengan langkah di README bagian Cara menjalankan: periksa SHA256 zip, ekstrak ke `models/`, lalu `python -m src.cek_penilai_fiktif` harus mencetak `KONTROL OK: 12 dari 12`.
- Skrip analisis (`eda_`, `cv_`, `ablate_`, `lofo_`, `lobo_brand`, `eval_`, dan lain-lain) dibekukan. Tiap skrip mencetak angka agregat yang dicatat di `docs/experiment_design.md` pada tahap yang sama, dan jalannya tertulis di docstring (`python -m src.NAMA` atau `python src/NAMA.py`). Beberapa punya kontrol bawaan, misalnya OOF 3245/1317/2584 dan 2513/2549. Tidak ada tes otomatis untuk skrip analisis.

## Batas yang diketahui

- Belum diuji dari nol oleh orang lain. Angka kontrol bisa berbeda bila berkas sumber berubah: hash unduhan Nazario dan tanggal akses file modern tidak tercatat.
- Ekstraksi memakai dua versi Python (3.14.3 lokal untuk SpamAssassin, 3.12.15 di Docker untuk Nazario). Pada 6047 email SpamAssassin hasil parser identik lintas versi; HTML bergaya phishing belum teruji lintas versi.
- Kelompok near-duplicate dihitung dari TF-IDF dan bisa berbeda halus antar versi library. Karena itu pembagian data dipakai dari daftar, bukan dihitung ulang.
- Daftar split hanya menunjukkan pembagian per `content_hash`; ia tidak membuktikan bahwa dataset bisa dibangun ulang dari sumber.
