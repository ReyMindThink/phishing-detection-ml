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

## Riwayat Perubahan

- (belum ada perubahan setelah Tahap 3)
