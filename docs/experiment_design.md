# Desain Eksperimen

Dokumen ini ditulis SEBELUM melatih model apa pun. Perubahan setelah melihat hasil harus dicatat di bagian "Riwayat Perubahan".

## Definisi Kelas

- **phishing**: email yang berusaha menipu penerima agar menyerahkan kredensial, data pribadi, atau uang, biasanya dengan menyamar sebagai pihak terpercaya.
- **spam**: email massal tak diinginkan yang tidak berusaha menyamar untuk mencuri data. Spam BUKAN phishing.
- **ham**: email sah.

## Keputusan

- Pendekatan: klasifikasi tiga kelas (ham / spam / phishing).
- Fokus: detektor email. Fitur URL diekstrak dari link di dalam email. Detektor URL murni bersifat opsional.
- Prioritas: precision kelas phishing, dengan syarat recall phishing minimal 90% (ditetapkan di Tahap 3, sebelum modeling). Recall dihitung pada data uji yang tidak dipakai saat latih. Threshold dipilih di data validasi.
- Metrik utama: PR-AUC kelas phishing dan macro-F1.
- Threshold dipilih dari kurva precision-recall pada data validasi.
- Risk score = probabilitas model (idealnya dikalibrasi), bukan skor heuristik.

## Risiko yang Diketahui

- Kelas berkorelasi dengan sumber data (jalan pintas). Diuji di Tahap 6.
- Data lama (era 2000-an), kemungkinan lemah terhadap phishing modern.
- Data dominan bahasa Inggris.
- Dataset phishing bisa mengandung label noise atau spam yang salah label.
- Kemungkinan duplikat lintas sumber (dicek di Tahap 3 dan 4).

## Keputusan Tahap 3 (dikunci sebelum modeling)

- Minimum recall phishing: 90%. Kalau tidak tercapai, dilaporkan apa adanya. Perubahan angka dicatat di bawah, lengkap dengan alasannya.
- Data bersih: buang email kosong (44, semuanya phishing) dan duplikat exact. Near-duplicate dikelompokkan dengan TF-IDF cosine >= 0,9 menjadi group_id. Satu grup tidak boleh terbelah ke train dan test.
- Ukuran jujur setelah pembersihan: ham 4110, spam 1810, phishing 3378 email (2038 grup phishing independen).
- Jalan pintas yang sudah teramati (diuji di Tahap 6): HTML vs teks biasa, header mailing list (hampir hanya ham), charset windows-1251 (23% phishing, hampir tidak ada di ham), charset kosong. Kelas juga identik dengan sumber data.
- MeAJOR: tidak untuk latih (format anonim memberi jalan pintas). Hanya uji eksternal false positive, setelah cek duplikat terhadap SpamAssassin dan normalisasi token anonim.

## Keputusan Tahap 4 (strategi split)

- Split: dua tahap dengan StratifiedGroupKFold, seed 42 dipilih sekali dan tidak diubah. Tahap 1 menyisihkan test set (1860 email, sekitar 20%) yang hanya dipakai sekali di evaluasi akhir. Tahap 2 membagi sisanya menjadi 5 lipatan CV. Threshold dipilih dari prediksi out-of-fold CV, bukan dari test.
- Kunci grup: grup teks (TF-IDF cosine >= 0,9) digabung dengan sender_domain khusus ham/spam. Dikecualikan dari penghubung grup: domain kosong, domain generik (muncul di lebih dari satu kelas, 49 domain, termasuk artefak spamassassin.taint.org), dan 5 domain jembatan (barrera.org, evergo.net, pobox.com, mithral.com, slack.net). sender_domain BUKAN fitur model.
- Domain pengirim phishing tidak dipakai sebagai kunci grup. Domainnya adalah merek yang ditiru, dan satu kit phishing dipakai untuk banyak merek: skenario B menyatukan 1382 email (40,9% phishing, 97 merek) ke satu grup sehingga split mustahil. Kemampuan menangani merek baru diuji terpisah (leave-brand-out, Tahap 8).
- Perbandingan skenario (grup terbesar sebagai % kelas): A teks saja ham 0,2 / spam 0,9 / phishing 2,0; B teks + domain semua kelas ham 17,7 / spam 8,7 / phishing 40,9; C teks + domain ham/spam ham 17,7 / spam 8,7 / phishing 2,0. Di C grup ham terbesar (726 email, 28 domain, 682 grup teks) dipecah dengan membuang 5 domain jembatan hingga di bawah 5% (4,6%).
- Pilihan peneliti yang kepekaannya harus diuji di Tahap 8: ambang cosine 0,9, ambang grup terbesar 5%, dan pemilihan jembatan berdasarkan jumlah domain tetangga.
- Hasil: 4741 grup; tidak ada grup terbelah antara train/test maupun antar-lipatan; proporsi kelas tiap bagian 44,2 / 19,5 / 36,3 (ham/spam/phishing). Indeks disimpan di data/processed/splits.csv (diabaikan Git; dibuat ulang dengan src/make_splits.py, seed 42).

### Keterbatasan split

- Grup dari kemiripan teks bisa melewatkan kampanye yang sama dengan kata berbeda.
- Email dari 5 domain jembatan boleh terbelah antara train dan test jika teksnya berbeda, jadi kebocoran pengirim di bagian itu tidak dikunci. Proporsi pastinya belum diukur.
- Domain layak berbeda antara train dan test tidak menjamin penulis berbeda.
- Phishing: 87,2% domain pengirim di test juga ada di train (424 dari 504 domain layak), jadi skor test optimis untuk merek yang sudah dikenal. Diukur ulang lewat leave-brand-out.
- Daftar domain generik dihitung dari seluruh data, termasuk bagian test (hanya untuk pengelompokan, bukan fitur).
- EDA Tahap 1-4 melihat seluruh data, termasuk test. Itu hanya diagnostik struktural; mulai Tahap 5, keputusan fitur dan model hanya memakai data train.
- 20051114.mbox hanya sekitar 1% phishing train dan tidak ada di test.

## Riwayat Perubahan

- Tahap 4: rencana awal memakai sender_domain untuk semua kelas diubah menjadi hanya ham/spam, karena hasil eksperimen menunjukkan grup phishing raksasa (40,9%). Keputusan "sender_domain bukan fitur" tidak berubah.
