# SOURCES

Catatan asal, lisensi, dan bias setiap sumber data. Data mentah TIDAK disertakan di repo ini.

## 1. SpamAssassin Public Corpus

- **URL halaman:** https://spamassassin.apache.org/old/publiccorpus/readme.html
- **URL direktori file:** https://spamassassin.apache.org/old/publiccorpus/
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

Tidak ada lisensi formal di halaman. Readme menyatakan hak cipta teks email tetap milik pengirim asli.
Konsekuensi: email mentah tidak di-commit ke repo.

### Catatan bias

- Email kira-kira berasal dari 2002-2005 (tanggal di nama file = tanggal perakitan, bukan tanggal email). Rentang pasti dicek dari header Date.
- Ham dan spam berasal dari satu sumber yang sama, berbeda dari sumber phishing (risiko jalan pintas).
- Sebagian header dikaburkan penyusun (alamat dan hostname).
- Penyusun melarang mengirim email korpus ke sistem email sungguhan.

## 2. MeAJOR (Merged email Assets from Joint Open-source Repositories)

- **URL halaman:** https://zenodo.org/records/18471483
- **DOI:** 10.5281/zenodo.18471483 (Versi 2.0, Februari 2026)
- **Penyusun:** Cardoso, F., Vitorino, J., Mendes, P., Maia, E., & Praça, I. (GECAD, ISEP, Politeknik Porto)
- **Tanggal unduh:** 2026-10-12
- **Lisensi:** Creative Commons Attribution 4.0 International (CC BY 4.0). Wajib mencantumkan atribusi.
- **Peran dalam proyek:** kandidat sumber phishing (dan pembanding ham/spam). Belum diputuskan baris mana yang dipakai.

### Sitasi

Cardoso, F., Vitorino, J., Mendes, P., Maia, E., & Praça, I. (2026). MeAJOR: Merged email Assets from Joint Open-source Repositories (Version 2.0) [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.18471483

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
- Nazario berasal dari kotak masuk pribadi satu orang, bukan sampel acak dunia nyata (dari hasil pencarian, belum diverifikasi ke sumber asli).

## 3. Phishing: dataset Kaggle

(belum diverifikasi)
