# Desain Eksperimen

Dokumen ini ditulis SEBELUM melatih model apa pun. Perubahan setelah melihat hasil harus dicatat di bagian "Riwayat Perubahan".

## Definisi Kelas

- **phishing**: email yang berusaha menipu penerima agar menyerahkan kredensial, data pribadi, atau uang, biasanya dengan menyamar sebagai pihak terpercaya.
- **spam**: email massal tak diinginkan yang tidak berusaha menyamar untuk mencuri data. Spam BUKAN phishing.
- **ham**: email sah.

## Keputusan

- Pendekatan: klasifikasi tiga kelas (ham / spam / phishing).
- Fokus: detektor email. Fitur URL diekstrak dari link di dalam email. Detektor URL murni bersifat opsional.
- Prioritas: precision kelas phishing, dengan batas minimum recall (angka ditetapkan di Tahap 3, sebelum modeling).
- Metrik utama: PR-AUC kelas phishing dan macro-F1.
- Threshold dipilih dari kurva precision-recall pada data validasi.
- Risk score = probabilitas model (idealnya dikalibrasi), bukan skor heuristik.

## Risiko yang Diketahui

- Kelas berkorelasi dengan sumber data (jalan pintas). Diuji di Tahap 6.
- Data lama (era 2000-an), kemungkinan lemah terhadap phishing modern.
- Data dominan bahasa Inggris.
- Dataset phishing bisa mengandung label noise atau spam yang salah label.
- Kemungkinan duplikat lintas sumber (dicek di Tahap 3 dan 4).

## Riwayat Perubahan

- (kosong)
