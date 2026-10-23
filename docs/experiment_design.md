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

## Hasil Uji Artefak Awal (setelah Tahap 4, hanya data train + 5 lipatan CV)

- Skrip: src/artifact_check_shape.py. Model: HistGradientBoosting default, seed 42, tanpa tuning; fitur hanya metadata bentuk email (tanpa teks, tanpa n_urls, tanpa sender_domain); encoder dilatih ulang per lipatan; prediksi out-of-fold digabung. Test set tidak disentuh. Baseline: akurasi tebak-kelas-terbanyak 0,442; PR-AUC phishing acak 0,363.
- Semua fitur bentuk: macro-F1 0,910, akurasi 0,925, PR-AUC phishing 0,995 (per lipatan 0,993-0,997); phishing precision 0,965 dan recall 0,967 pada tebakan terbanyak tanpa menyetel threshold. Target recall >= 90% tercapai tanpa membaca teks, jadi memenuhi target BUKAN bukti model mendeteksi phishing.
- Satu kelompok sendirian (PR-AUC phishing): html 0,892; header 0,979; charset 0,678. Semua fitur kecuali satu kelompok: tanpa html 0,989; tanpa header 0,960; tanpa charset 0,991. Jalan pintas berlapis: membuang satu kelompok tidak cukup.
- Satu fitur sendirian: n_headers 0,803; content_type 0,771; html_bytes 0,765; plain_bytes 0,698; has_html 0,688; has_plain 0,686; charset 0,678; n_received 0,556; has_list_header 0,541; has_mailman 0,530; has_x_mailer 0,420; n_parts 0,364; has_message_id 0,363. Penyebab kuatnya n_headers belum diketahui (n_received sendirian lemah, jadi bukan jumlah hop).
- ID sumber: subset menentukan label 100% (nazario hanya phishing; spamassassin hanya ham/spam; 0 subset campur label). Ini tautologi, dilaporkan sebagai bukti, bukan sebagai model.
- Keterbatasan: hanya satu algoritma dan satu seed, tanpa tuning; PR-AUC fitur biner sendirian dibatasi bentuknya (dua tingkat skor); ham vs spam juga mudah dibedakan dari bentuk, belum dibedakan apakah itu perbedaan wajar atau artefak subset.
- Implikasi untuk Tahap 6 (belum diputuskan): tolok ukur "model sungguhan harus lebih baik dari model curang" tidak memadai pada batas 0,995. Calon pengganti: evaluasi pada subset email HTML tanpa header mailing list; uji eksternal MeAJOR dan phishing modern 2015-2025.

## Bedah n_headers (data train saja)

- Skrip: src/eda_n_headers.py. Median n_headers per subset: easy_ham 30, easy_ham_2 30, hard_ham 13; spam 18, spam_2 16; phishing0 20, phishing1 25, phishing2 21, phishing3 23, 20051114 31 (hanya 26 email di train, jangan ditafsirkan berlebihan).
- Dugaan awal "phishing punya header lebih sedikit daripada ham/spam" hanya sebagian benar: phishing berada di antara spam (lebih sedikit) dan easy_ham (lebih banyak). Persen email dengan n_headers <= 15: ham 22,5, spam 37,8, phishing 1,4; <= 30: ham 54,8, spam 95,1, phishing 92,6.
- Phishing hampir tidak pernah punya header sangat sedikit: minimum tiap file Nazario sekitar 14-18 (kecuali phishing1: 6). Pola "lantai" ini konsisten dengan header tambahan dari sistem penerima pengumpul, tetapi BELUM diverifikasi (butuh nama header, bukan jumlah).
- Subset dalam satu kelas berbeda jauh: hard_ham (median 13, header mailing list 9,6%) mirip spam, sedangkan easy_ham_2 97,1% punya header mailing list. File Nazario juga berbeda antar sesamanya (phishing0 sempit 16-24, phishing1 lebar 19-35, rentang 10%-90%), jadi model bisa mengenali file atau era, bukan hanya kelas.
- Kesimpulan sementara: n_headers mencampur sifat email yang wajar dan cara korpus disimpan; keduanya belum bisa dipisahkan dari jumlah saja.
- Rencana (belum diputuskan): saat re-ekstraksi di Tahap 5, tambahkan kolom diagnostik berisi NAMA header saja (tanpa isi), hanya untuk menguji dugaan di atas, bukan sebagai fitur model.

## Keputusan Tahap 5 (fitur link)

- Yang disimpan dari link: angka ringkas dan daftar host tujuan (defanged, tanpa path, tanpa URL lengkap). Fitur URL numerik dihitung di dalam parser.
- Fungsi: fitur_link() di src/email_parser.py, satu fungsi yang SAMA untuk semua kelas. Tahap 5b menjalankan ulang ekstraksi SpamAssassin dan Nazario dengan fungsi yang sama. parse_pesan() tidak diubah: n_urls lama tetap ada tetapi tetap tidak boleh dipakai sebagai fitur (hanya membaca URL di teks tampil, bukan href).
- Definisi: n_links = jumlah URL http(s) unik (href di HTML + URL di teks biasa); "domain" = host lengkap termasuk subdomain (belum memakai daftar public suffix); mismatch = teks link tampak seperti domain tetapi host tujuan berbeda (www. diabaikan, subdomain dianggap sama).
- Tes: tests/test_email_parser.py, 13 tes lolos, termasuk kasus tepi (HTML rusak, tanpa link, skema mailto/javascript/relatif, deduplikasi).
- Risiko menghafal artefak dan cara menguji:
  - n_links, n_link_domains, n_images, n_forms: hanya HTML yang punya tag <a>/<img>, risiko meniru "HTML = phishing". Uji di subset HTML saja dan model tanpa kelompok ini.
  - n_link_mismatch: newsletter sah memakai domain pelacak, jadi ham bisa salah tuduh. Uji lewat error analysis false positive di ham.
  - n_link_ip, n_link_userinfo, n_link_punycode: pola era 2003-2007, bisa basi untuk phishing modern. Uji lewat phishing modern 2015-2025 (Tahap 8).
  - max_url_len, max_host_labels: URL pelacak newsletter modern panjang, distribusi bergeser. Uji lewat MeAJOR.
- Keterbatasan: teks link seperti "Mr.Smith" bisa terbaca sebagai domain (mismatch palsu); link di atribut lain (action form, src gambar) belum dihitung; tanpa daftar public suffix; link yang disamarkan lewat redirect tidak terdeteksi.

## Hasil Tahap 5b (ekstraksi ulang dengan fitur link)

- Kolom baru (12): n_links, n_link_domains, domains_link_defanged, n_link_mismatch, n_link_ip, n_link_userinfo, n_link_punycode, max_url_len, max_host_labels, n_images, n_forms, header_names. header_names (nama header unik tanpa isi) hanya diagnostik, BUKAN fitur model, dan belum dianalisis. emails_clean.csv sekarang 9298 baris, 37 kolom (25 + 12).
- Bukti data lama tidak bergeser: 23 kolom lama SpamAssassin dan 21 kolom lama Nazario identik dengan ekstraksi lama (src/check_extraction_same.py), gagal=0 di semua subset dan file; sidik jari content_hash, isi splits.csv, dan partisi grup (7271 grup; src/fingerprint_data.py dan src/fingerprint_groups.py) sama persis, jadi make_splits.py tetap menghasilkan split yang sama. splits.csv tidak dibuat ulang.
- Lingkungan ekstraksi: SpamAssassin di Python 3.14.3 (lokal), Nazario di Docker Python 3.12.15. Uji lintas versi (src/env_digest.py) pada 6047 email SpamAssassin: 0 perbedaan pada teks, metadata, fitur link, header_names, dan domain. Batas: SpamAssassin sebagian besar teks biasa, jadi HTML ala phishing belum teruji lintas versi.
- % email yang punya link, n_urls lama vs n_links baru: easy_ham 80,1 vs 80,1; easy_ham_2 96,9 vs 97,2; hard_ham 82,0 vs 96,4; spam 58,4 vs 83,2; spam_2 53,6 vs 77,8; Nazario 62,0-75,1 vs 94,4-98,9 (rentang per file). Pada teks biasa kedua fungsi sepakat; selisih hanya muncul di HTML. Ini membenarkan larangan memakai n_urls.
- n_link_mismatch > 0: phishing 44,0-52,9% (rentang per file), spam 0,6-1,0%, hard_ham 18,0%, easy_ham dan easy_ham_2 0,0%. Host berupa IP: phishing 19,5-47,1% (sangat berbeda antar file, jadi model bisa mengenali file atau era), spam 11,0-16,0%, ham 0,0-1,6%.
- Peringatan penafsiran: fitur link, mismatch, form, dan gambar bernilai nol menurut konstruksi pada email teks biasa, sehingga perbandingan antar kelas bercampur dengan perbedaan format (HTML). Nilai fitur ini harus dinilai di dalam subset email HTML, di data train.
- Duplikat exact (866 kelompok, 2624 email; ham 23, spam 71, phishing 772 kelompok): fitur angka link stabil antar salinan (phishing: n_links beda di 3,0% kelompok, n_link_domains 2,5%, n_link_mismatch 0,3%, n_images 0,6%, n_forms 0,0%; ham dan spam 0,0-1,4%). Tetapi daftar host tujuan berbeda pada 28,1% kelompok phishing. Akibatnya fitur berbasis identitas host (misalnya domain link vs domain pengirim) belum aman diambil dari salinan pertama. Opsi, belum diputuskan: gabungkan host dari semua salinan sebelum duplikat dibuang (aman karena duplikat exact selalu satu grup dan satu split).
- Keterbatasan: fitur link diambil dari salinan pertama untuk duplikat exact; penyebab perbedaan host antar salinan belum diselidiki.

## Riwayat Perubahan

- Tahap 4: rencana awal memakai sender_domain untuk semua kelas diubah menjadi hanya ham/spam, karena hasil eksperimen menunjukkan grup phishing raksasa (40,9%). Keputusan "sender_domain bukan fitur" tidak berubah.
- Setelah Tahap 4: uji artefak awal menunjukkan model hanya-bentuk mencapai PR-AUC phishing 0,995, sehingga tolok ukur Tahap 6 ("model sungguhan harus lebih baik dari model curang") perlu diganti. Penggantinya diputuskan di Tahap 6, bukan sekarang.
- Tahap 5b: kolom diagnostik header_names ditambahkan saat ekstraksi ulang (rencana di bagian "Bedah n_headers" terlaksana); tidak ada keputusan sebelumnya yang diubah.
