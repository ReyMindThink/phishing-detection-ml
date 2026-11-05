# SOURCES

Catatan asal, lisensi, dan bias setiap sumber data. Data mentah TIDAK disertakan di repo ini.

URL ditulis defanged (hxxps = https, [.] = titik): pulihkan dulu bila ingin membuka, dan jangan membuka berkas korpus phishing di browser atau klien email biasa.

## 1. SpamAssassin Public Corpus

- **URL halaman:** hxxps://spamassassin[.]apache[.]org/old/publiccorpus/readme[.]html
- **URL direktori file:** hxxps://spamassassin[.]apache[.]org/old/publiccorpus/
- **Tanggal unduh:** 2026-10-12
- **Peran dalam proyek:** kelas ham dan spam

### File yang dipakai (set 20030228)

| File                        | Isi menurut readme             | Dipakai sebagai                            | Ukuran (byte) | SHA-256                                                          |
| --------------------------- | ------------------------------ | ------------------------------------------ | ------------- | ---------------------------------------------------------------- |
| 20030228_easy_ham.tar.bz2   | 2500 non-spam, mudah dibedakan | ham                                        | 1612216       | 2b7b65904bcfcc31d2b5f51946f2d261370b257402cbbd62930b46ab83367438 |
| 20030228_easy_ham_2.tar.bz2 | 1400 non-spam, tambahan        | ham                                        | 1077892       | b4bd3dc5ae5b40f38e99a0e41ad7d16b428b56e818e3a6ffa07330d62004dd38 |
| 20030228_hard_ham.tar.bz2   | 250 non-spam, mirip spam       | ham                                        | 1029898       | ce2ce67880643dbde65ea7f85bffbfe4417349c4bd80b6b0de56262ae6b0a9c9 |
| 20030228_spam.tar.bz2       | 500 spam                       | spam                                       | 1183768       | c08debc32413804949a866be45ef78195cec2cbafd1da744ed76cdb860589743 |
| 20030228_spam_2.tar.bz2     | 1397 spam, tambahan            | spam (perlu verifikasi vs 20050311_spam_2) | 2059563       | 40bc444c596ff3e71505ae334f115b16f9b946786ee68f09b921b6b99217fd00 |

Set 20021010 sengaja ditunda karena kemungkinan tumpang tindih. Jumlah per file di atas
adalah klaim readme dan HARUS diverifikasi dengan menghitung file setelah diekstrak.

### Keutuhan file

Hash di atas dihitung dari file yang diunduh pada tanggal di atas. Halaman sumber tidak
menyediakan checksum pembanding, jadi hash hanya menjamin file tidak berubah sejak diunduh,
bukan bahwa isinya identik dengan yang dipublikasikan.

### Lisensi

Tidak ada lisensi formal di README korpus. Teks README (dicek 4 Nov 2026 lewat salinan di arsip milis 2002 dan 2011 serta skrip dataset pihak ketiga; halaman aslinya tidak dibuka langsung) menyatakan: pesan berasal dari forum publik, dikirim ke penyusun dengan sepengetahuan bahwa boleh dipublikasikan, ditulis penyusun, atau buletin situs berita publik; hak cipta teks pesan tetap milik pengirim asli.
Konsekuensi: email mentah tidak di-commit ke repo, dan repo ini TIDAK menyatakan lisensi apa pun atas data ini.

### Catatan bias

- Email kira-kira berasal dari 2002-2005 (tanggal di nama file = tanggal perakitan, bukan tanggal email). Rentang pasti dicek dari header Date.
- Ham dan spam berasal dari satu sumber yang sama, berbeda dari sumber phishing (risiko jalan pintas).
- Sebagian header dikaburkan penyusun (alamat dan hostname).
- Penyusun melarang mengirim email korpus ke sistem email sungguhan.

## 2. MeAJOR (Merged email Assets from Joint Open-source Repositories)

- **URL halaman:** hxxps://zenodo[.]org/records/18471483
- **DOI:** 10.5281/zenodo.18471483 (Versi 2.0, Februari 2026)
- **Penyusun:** Cardoso, F., Vitorino, J., Mendes, P., Maia, E., & Praça, I. (GECAD, ISEP, Politeknik Porto)
- **Tanggal unduh:** 2026-10-12
- **Lisensi:** Creative Commons Attribution 4.0 International (CC BY 4.0). Wajib mencantumkan atribusi.
- **Peran dalam proyek:** HANYA uji eksternal false positive (ham/spam asing), tidak dipakai untuk latih. Diputuskan di Tahap 3.
- **Temuan verifikasi (Tahap 8-3; rincian di docs/experiment_design.md):** kolom source hanya berisi trec5/trec6/trec7, tetapi 97 baris berlabel 1 mirip (cosine >= 0,9) dengan phishing Nazario di data latih. Jadi kolom source tidak dapat dipercaya, dan "MeAJOR tidak berisi phishing" TIDAK boleh ditulis. Karena label 1 bercampur (kemungkinan spam dan penipuan), recall phishing tidak diukur dengan data ini.

### Sitasi

Cardoso, F., Vitorino, J., Mendes, P., Maia, E., & Praça, I. (2026). MeAJOR: Merged email Assets from Joint Open-source Repositories (Version 2.0) [Dataset]. Zenodo. hxxps://doi[.]org/10[.]5281/zenodo[.]18471483

### File

| File                                     | Ukuran (byte) | MD5 (cocok dengan Zenodo)        | SHA-256                                                          |
| ---------------------------------------- | ------------- | -------------------------------- | ---------------------------------------------------------------- |
| meajor_cleaned_preprocessed.parquet.gzip | 86278230      | 78e397ad8447bcdba5a98097921ba8bd | 5a9de6c207634f068928ed0cc68d78ee2fd594ed9a587daf4048974c95715c1a |

### Isi menurut halaman Zenodo (klaim penyusun, belum diverifikasi)

- 108685 sampel; label 0 = benign, 1 = phishing (tidak ada kelas spam).
- Gabungan dari: TREC-05, TREC-06, TREC-07, Nazario Phishing Corpus, Nigerian Fraud.
- Teks dianonimkan dengan token seperti [URL], [EMAIL_ADDRESS], [NAME]; ada kolom sumber dan fitur hasil ekstraksi.

### Catatan bias dan risiko (hipotesis, diuji di tahap berikutnya)

- Label 1 kemungkinan mencampur spam dan penipuan (Nigerian Fraud), padahal definisi proyek: spam bukan phishing.
- Header mentah dan URL asli hilang (dianonimkan), sehingga fitur header/URL mentah tidak sebanding dengan SpamAssassin.
- Kemungkinan tumpang tindih dengan korpus era yang sama (misalnya TREC vs SpamAssassin). Dicek dengan hash isi.
- Nazario berasal dari kotak masuk pribadi satu orang, bukan sampel acak dunia nyata (didukung makalah arXiv 2408.08967 "Phishing Codebook"; README asli tidak dibuka ulang).

## 3. Nazario Phishing Corpus

- **URL halaman:** hxxps://monkey[.]org/~jose/phishing/
- **Penyusun:** José Nazario (koleksi dari inbox pribadi, diklasifikasi manual)
- **Tanggal akses:** 2026-10-13
- **Lisensi:** CC BY 4.0 (diverifikasi 5 Nov 2026: README.txt dan LICENSE.txt di halaman sumber, teks lengkap dibaca). README menyebut karya turunan dan pemakaian komersial diizinkan dengan atribusi. Wajib atribusi dan menyatakan perubahan.
- **Peran dalam proyek:** kelas phishing (set klasik)

### File yang dipakai

phishing0.mbox, phishing1.mbox, phishing2.mbox, phishing3.mbox, 20051114.mbox.
Tidak dipakai: private-phishing4.mbox (tidak dijelaskan di README).

### File modern (HANYA uji generalisasi, tidak untuk latih)

- 11 file phishing-2015 sampai phishing-2025; lisensi CC BY 4.0 (diverifikasi 5 Nov 2026 dari README.txt sumber; README itu berlaku untuk seluruh direktori dan tidak memisahkan file klasik dari modern). Wajib atribusi.
- Pemeriksaan HEAD sebelum unduh: 11 file HTTP 200, Content-Length 8815568 sampai 18769863 byte. Ekstraksi hanya di Docker (--rm) dengan src/extract_nazario_modern.py (komit 09531e5).
- Hasil: 3466 email (2015 307, 2016 494, 2017 325, 2018 288, 2019 243, 2020 158, 2021 101, 2022 247, 2023 419, 2024 403, 2025 481); 0 gagal; 84 body_text kosong. CSV 7898810 byte, diabaikan Git.
- Tidak dicatat saat pengambilan (utang dokumentasi): hash berkas unduhan dan tanggal akses (mbox tidak disimpan). Tanggal komit 09531e5 hanya perkiraan kasar.

### Cara pengambilan (penting untuk keamanan)

File mbox TIDAK disimpan di Windows. Antivirus (Windows Defender) menandai unduhan browser
karena berisi lampiran malware sungguhan (Mydoom, Mytob, Hupigon, Vigorf) di phishing1/phishing2,
bertentangan dengan klaim README bahwa file "seharusnya tidak berisi malware".
Pipeline: src/extract_nazario.py berjalan di dalam container Docker, mengunduh ke memori,
membuang lampiran dan HTML, lalu hanya mengeluarkan CSV teks bersih.

### Hasil ekstraksi (diverifikasi 2026-10-13)

| File      | Email                                         |
| --------- | --------------------------------------------- |
| phishing0 | 414                                           |
| phishing1 | 456                                           |
| phishing2 | 1423                                          |
| phishing3 | 2279                                          |
| 20051114  | 438                                           |
| Total     | 5010 (3379 unik berdasarkan hash teks persis) |

### Catatan bias dan risiko

- Inbox pribadi satu orang: representatif, bukan sampel acak.
- Dilabel manual, mungkin ada kesalahan (menurut README).
- Banyak duplikat (1631) dan tumpang tindih antar file (339 hash).
- Hampir semua email berformat HTML, berbeda dari ham SpamAssassin (risiko jalan pintas format).
- URL di atribut href belum terambil oleh parser versi ini.
