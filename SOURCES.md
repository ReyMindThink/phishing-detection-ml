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

## 2. Phishing: Nazario corpus

(belum diverifikasi)

## 3. Phishing: dataset Kaggle

(belum diverifikasi)
