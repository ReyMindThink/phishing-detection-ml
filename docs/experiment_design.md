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
- Tes: tests/test_email_parser.py, 14 tes lolos, termasuk kasus tepi (HTML rusak, tanpa link, skema mailto/javascript/relatif, deduplikasi).
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

## Hasil Tahap 5c-1 (EDA fitur link, hanya email HTML, data train)

- Skrip: src/eda_link_html.py. Split terbukti: train 7438 (ham 3288, spam 1448, phishing 2702), test 1860; test dibuang di awal skrip. Email HTML di train: 3474 (ham 142, spam 789, phishing 2543). PR-AUC phishing acak di dalam subset HTML = 0,732 (bukan 0,363).
- Ukuran sel: ham HTML hampir semuanya hard_ham (124 dari 142); easy_ham 5 dan easy_ham_2 13 email HTML (n < 30, tidak ditafsirkan). Ham HTML per lipatan CV = 24/10/9/90/9: 63% ada di satu lipatan, tiga lipatan hanya punya 9-10 contoh.
- Median n_links: ham 34, spam 2, phishing 1. n_link_mismatch > 0: ham 31,7%, spam 1,6%, phishing 53,7% (empat file Nazario besar 49,2-57,7; dua subset spam 1,4-1,7). Mismatch memisahkan phishing dari spam dengan baik tetapi lemah terhadap ham HTML (newsletter memakai domain pelacak; hard_ham 36,3%).
- n_link_ip > 0: ham 1,4%, spam 16,5%, phishing 24,3% (empat file besar 16,0-43,2): sangat beda antar file, risiko mengenali file/era.
- n_forms > 0: ham 38,0%, spam 19,1%, phishing 2,3%. Berlawanan dengan intuisi phishing modern: di data 2003-2007 form tertanam ada di newsletter sah (hard_ham 42,7%). Model akan belajar "ada form = ham"; pola ini bisa terbalik pada phishing modern.
- n_images > 0: ham 86,6%, spam 49,6%, phishing 74,0 (hard_ham 97,6%).
- Prediksi vs hasil: IP spam meleset (prediksi 20-30%, hasil 16,5%; link IP spam juga ada di teks biasa). Lainnya sesuai.
- Keterbatasan: kesimpulan tentang ham HTML bersandar pada satu subset (hard_ham) dan satu lipatan; persen tanpa interval kepercayaan; belum ada uji model (5c-2).

## Hasil Tahap 5c-2 (uji CV fitur link di dalam email HTML, data train)

- Skrip: src/cv_link_html.py. 3474 email HTML train (ham 142, spam 789, phishing 2543), HistGradientBoosting default, seed 42, 5 lipatan dari splits.csv, test tidak disentuh. PR-AUC phishing acak di subset ini 0,732. Dua subkelompok: tujuan (n_links, n_link_domains, n_link_mismatch, n_link_ip, n_link_userinfo, n_link_punycode, max_url_len, max_host_labels) dan letak (n_images, n_forms).
- PR-AUC phishing (per lipatan): bentuk saja 0,997 (0,996-0,998); bentuk+tujuan 0,999; bentuk+letak 0,997; bentuk+tujuan+letak 0,999; tujuan saja 0,968; letak saja 0,844; tujuan+letak 0,976. AUC phishing vs spam: bentuk 0,992, bentuk+tujuan 0,996, tujuan saja 0,912. AUC vs ham (n=142, 63% di satu lipatan, tidak ditafsirkan): bentuk 0,996, tujuan saja 0,900.
- Selisih berpasangan terhadap bentuk saja: tujuan +0,0014 (membaik 5 dari 5 lipatan), letak +0,0003 (3 dari 5), keduanya +0,0017 (5 dari 5). Aturan dikunci (selisih >= 0,005 dan >= 4 dari 5 lipatan): tidak ada yang lolos.
- Penafsiran: efek langit-langit. Fitur bentuk saja sudah 0,997 di dalam HTML, jadi PR-AUC tidak cukup peka untuk menilai nilai tambah link. Ini bukan bukti link tak berguna. Fitur link sendirian cukup kuat, tetapi belum bisa dipisahkan antara sinyal isi dan gaya sumber/era (IP berbeda antar file, n_forms berarah terbalik, spam dan phishing beda sumber).
- Prediksi vs hasil: PR-AUC bentuk (prediksi 0,96-0,995, hasil 0,997) dan tujuan saja (prediksi 0,85-0,93, hasil 0,968) meleset karena kekuatan link diremehkan; lainnya sesuai.
- Keterbatasan: lima lipatan memakai data latih yang tumpang tindih, jadi "membaik di 5 dari 5" bukan uji signifikansi; satu algoritma dan satu seed; ham HTML hanya 142.
- Keputusan: kedua subkelompok tetap kandidat. Pemakaian akhir ditentukan di Tahap 6-7 setelah uji artefak.

## Rencana Tahap 5d (fitur teks; ditulis sebelum model teks dijalankan)

- Prinsip: TF-IDF (kosakata dan bobot IDF) di-fit hanya pada lipatan latih di dalam tiap putaran CV (Pipeline). Vektorizer tidak pernah melihat lipatan validasi maupun test. Hanya data train.
- Kelompok fitur, risiko menghafal artefak, dan cara menguji:
  1. TF-IDF kata dari teks email. Risiko: sisa footer milis, kutipan balasan, nama orang atau situs era 2002-2007, tahun, nama merek (merek yang ditiru sah sebagai sinyal tetapi terikat era), sisa teks CSS atau skrip dari HTML. Uji: (a) cetak kata berbobot tertinggi per kelas (hanya kata, tanpa isi email) lalu tandai yang bersifat artefak; (b) leave-one-file-out untuk phishing: latih tanpa satu file Nazario, uji di file itu (20051114 tidak ditafsirkan, hanya 26 email di train); (c) ablasi: buang daftar kata artefak yang ditandai, ukur penurunan PR-AUC.
  2. Kata urgensi (daftar tulis tangan). Risiko: daftar disusun dari prasangka peneliti, dan spam serta newsletter juga memakai urgensi. Uji: persen email berisi kata urgensi per kelas dan per subset; bandingkan phishing vs spam di dalam email HTML.
  3. Statistik teks sederhana (panjang, rasio huruf besar, rasio angka). Risiko: proksi format dan sumber. Uji: PR-AUC fitur sendirian dan di dalam subset HTML.
  4. Subjek (bila dipakai). Dugaan yang harus diukur: subjek ham membawa tag milis (misalnya berawalan "[") dan "Re:". Uji: persen subjek berawalan "[" dan "Re:" per kelas dan per subset.
- Ukuran jujur: jangan menyimpulkan dari satu subset; sebut n tiap sel.

## Hasil Tahap 5d-2 (model teks pertama, hanya body_text, data train)

- Skrip: src/cv_text.py. TfidfVectorizer (token huruf >= 3, min_df 3, maks 20000 fitur, sublinear_tf) + LogisticRegression (seed 42) dalam satu Pipeline, di-fit hanya di lipatan latih (kosakata 15537-16909 per lipatan). 5 lipatan dari splits.csv, test tidak disentuh.
- Semua train (n=7438): macro-F1 0,955; akurasi 0,961 (dari confusion matrix); PR-AUC phishing 0,994 (per lipatan 0,990-0,997; acak 0,363); AUC phishing vs spam 0,992, vs ham 0,997. Confusion matrix (benar -> tebakan ham/spam/phishing): ham 3245/30/13; spam 83/1317/48; phishing 71/47/2584. Phishing: precision 0,977 (2584/2645), recall 0,956 (2584/2702).
- Di dalam email HTML (n=3474; acak 0,732): PR-AUC phishing 0,998 (per lipatan 0,996-1,000); AUC phishing vs spam 0,995 (n=3332).
- Recall phishing per file: 20051114 0,962 (n=26, tidak ditafsirkan), phishing0 0,859 (n=248), phishing1 0,978 (n=267), phishing2 0,945 (n=757), phishing3 0,976 (n=1404).
- Prediksi vs hasil: macro-F1 dan PR-AUC semua sesuai rentang. PR-AUC di HTML (0,998) dan AUC vs spam di HTML (0,995) di atas rentang prediksi. Recall >= 0,95 hanya terpenuhi di 2 dari 4 file besar (phishing0 dan phishing2 di bawahnya).
- Penafsiran: model teks tanpa fitur bentuk (0,994) hampir setara model bentuk tanpa teks (0,995). Dua jalur berbeda mendekati langit-langit yang sama, jadi keduanya mungkin menangkap perbedaan sumber yang sama (sisa HTML, footer milis, gaya era), bukan niat phishing. Aturan: skor >= 0,99 dicurigai artefak; belum diuji. Pipeline mencegah kebocoran TF-IDF antar lipatan; kebocoran kampanye berkata berbeda masih mungkin.
- Keterbatasan: satu algoritma, satu seed, tanpa tuning; keputusan argmax tanpa threshold; sebab recall rendah di phishing0 belum diselidiki; prevalensi data tidak realistis.

## Hasil Tahap 5d-3 (kata stabil dan phishing0, data train)

- Skrip: src/words_text.py. 30 kata teratas per kelas (koefisien Logistic Regression) per lipatan; stabil = muncul di >= 4 dari 5 lipatan: ham 27, spam 22, phishing 28 dari 30. Persen email per kelas yang memuat kata dihitung deskriptif di train, bukan input model.
- Ham: kata stabil hampir semuanya jejak sumber (milis dan topik korpus): listinfo 52,3% ham vs 0,1% phishing, mailman 41,7% vs 0,1%, wrote 35,7% vs 0,2%, juga rpm, razor, spamassassin, linux. Model teks mengenali ham lewat footer milis, jalan pintas yang sama dengan has_list_header pada fitur bentuk.
- Spam: kata promosi (free 46,1%, remove/removed, click, money, guaranteed, investment, opt).
- Phishing: kata akun dan merek (account 62,4%, paypal 27,7% vs 0,3% ham, ebay 20,8%, bank, security, confirm, update, customer, member); tidak ada fragmen URL. Terikat era dan merek 2003-2007. Kata umum (your 82,7%, please 73,9%, thank 54,6%) juga tinggi di spam. Anomali BELUM dipahami: nama (annie, paul) dan kata ganti (had, him, his, she, her) masuk teratas phishing padahal jarang di phishing (2-8%); koefisien multinomial bersifat relatif antar kelas, belum diuji.
- phishing0 (train, n=248): terdeteksi 213, terlewat 35 (recall 0,859); salah ke spam 19, ke ham 16. Terlewat vs terdeteksi: median panjang teks 2103 vs 1187 karakter, HTML 74,3% vs 94,4%. 11 dari 35 terlewat berbagi token yang sama (gnu, gnupg, pgp, signature, linux, mailer, dan token acak): pola email teknis ber-PGP. Dugaan (BELUM diverifikasi): label noise, satu kelompok duplikat, atau email forward.
- Prediksi vs hasil: kestabilan, kosakata akun/merek, dan kata milis ham sesuai; fragmen URL tidak muncul; terlewat ke ham tidak dominan (spam 19 vs ham 16); terlewat justru lebih panjang, bukan lebih pendek.
- Keterbatasan: persen deskriptif, bukan pentingnya fitur; kestabilan lintas lipatan memakai data latih yang tumpang tindih; satu model dan satu seed; hanya 35 email terlewat.

## Hasil Tahap 5d-4 (error analysis phishing terlewat, model teks, data train)

- Skrip: src/error_phishing_missed.py (pipeline sama dengan cv_text.py; assert membuktikan hasil identik: phishing0 terdeteksi 213, terlewat 35). Phishing terlewat 118 dari 2702 (recall 0,956): 20051114 1, phishing0 35, phishing1 6, phishing2 42, phishing3 34; per lipatan 19/27/25/31/16.
- Email train yang memuat gnupg: ham 27 (easy_ham 18, easy_ham_2 9), phishing 12 (phishing0 11, phishing3 1). Model belajar "gnupg = ham".
- Kluster phishing0 terlewat yang memuat gnupg: 11 email, semuanya satu group_id (satu grup final, satu lipatan, ukuran grup di train tepat 11, semuanya berlabel phishing), semuanya ditebak ham; median teks 213 karakter, 100% HTML, 0% header milis, median n_headers 19; semuanya juga memuat pgp. Seluruh phishing0 yang memuat gnupg (11 dari 11) terlewat. Di luar phishing0 hanya 1 dari 83 terlewat yang memuat gnupg.
- Penafsiran: kegagalan karena jalan pintas (kata sumber ham mengalahkan bukti phishing), BUKAN label noise. Hipotesis (belum diperiksa): satu kampanye menambahkan blok tanda tangan PGP. Tanpa kluster, recall phishing0 = 213/237 = 0,899 (hitungan, bukan alasan membuang data). Kesalahan tersisa phishing0 (24): spam 19, ham 5; HTML 15 dari 24 (62,5%).
- Koreksi: catatan 5d-3 yang mengaitkan kluster ini dengan teks lebih panjang dan kurang HTML salah. Kluster pendek dan 100% HTML; selisih itu berasal dari 24 email terlewat lainnya.
- Implikasi untuk Tahap 8: lapor recall per email DAN per grup, karena satu grup near-duplicate bisa mewakili banyak kesalahan.
- Keterbatasan: satu model dan satu seed; sifat kampanye belum diperiksa langsung; test set tidak disentuh.

## Hasil Tahap 5d-5 (kesalahan phishing per email dan per grup, model teks, data train)

- Skrip: src/error_by_group.py (pipeline sama dengan cv_text.py; assert: phishing terlewat 118). Grup memakai group_final; 1629 grup berisi phishing, 0 di antaranya campur kelas (jadi untuk phishing sama dengan grup teks).
- Recall phishing: per email 0,956 (2702 email); per grup 0,946 (rata-rata recall tiap grup, bobot sama). Grup terdeteksi semua 1541, sebagian 1 (5 dari 7), terlewat semua 87; 88 grup punya >= 1 kesalahan.
- Menurut ukuran grup (n_grup / n_email / recall email / recall grup): 1 = 1281/1281/0,938/0,938; 2-5 = 300/819/0,977/0,980; 6-20 = 44/428/0,953/0,948; >20 = 4/174/1,000/1,000 (hanya 4 grup, petunjuk saja).
- Konsentrasi: grup teratas 11 dari 118 kesalahan (9,3%); 3 teratas 19,5%; 5 teratas 25,4%; 10 teratas 33,9%. 79 grup masing-masing hanya punya 1 kesalahan. Di phishing0, 30 dari 35 kesalahan ada di 6 grup (kampanye terlewat utuh, termasuk kluster gnupg 11 email). phishing2 (42) dan phishing3 (34) kesalahannya tersebar di email tunggal atau grup kecil.
- Prediksi vs hasil: recall per grup diprediksi LEBIH TINGGI dari per email, hasilnya lebih rendah (0,946 vs 0,956; kesalahan banyak berupa email tunggal, bukan menumpuk di grup besar). Konsentrasi 5 teratas (>= 25%), jumlah grup ber-kesalahan (<= 100), dan grup tunggal lebih lemah dari grup > 20 sesuai prediksi.
- Penafsiran: ada dua pola kesalahan (kampanye utuh terlewat di phishing0; email tunggal tersebar di phishing2 dan phishing3). Phishing "unik" (grup tunggal, 79% grup, 47% email) lebih sulit (0,938). Recall per email sedikit lebih optimis daripada per grup.
- Keterbatasan: satu model dan satu seed; grup > 20 hanya 4; penyebab kesalahan email tunggal belum dianalisis; angka hanya untuk data train lama, bukan phishing modern.

## Hasil Tahap 5d-6 (EDA subjek, kata urgensi, statistik teks, data train)

- Skrip: src/eda_text_extras.py. Daftar kata tulisan tangan (bahasa Inggris), disusun dari prasangka peneliti sebelum diukur. ANCAMAN: urgent, immediately, suspend(ed), expire(s/d), locked, unauthorized/unauthorised, terminated/termination, deactivated/deactivation, restricted, warning, alert. AKSI: verify, confirm, validate, login, log in, sign in, password.
- Subjek (semua train; ham/spam/phishing): awalan "[" 15,5/5,2/2,8%; awalan "Re:" 53,5/3,9/1,0% (easy_ham_2 71,2%; di dalam HTML ham hanya 4,9%, n=142); subjek kosong di bawah 1%. "Re:" menyerupai jalan pintas header milis (utas balasan ham, hampir tidak ada di phishing), terikat korpus.
- Kata urgensi, email HTML (ham/spam/phishing): ancaman 12,7/10,5/36,5%; aksi 14,8/2,3/51,2%. Antar file phishing: aksi 37,3% (phishing3) sampai 74,5% (phishing1), ancaman 28,2 sampai 49,6%, jadi sinyalnya searah tetapi terikat sumber dan era. hard_ham HTML (n=124) 16,9% memuat kata aksi: risiko false positive pada email transaksional sah.
- Statistik teks: median rasio huruf besar spam 9,4%, ham dan phishing 5,3% (HTML 10,2/8,5/5,3). Median rasio angka phishing 0,9% vs ham 1,6% dan spam 1,8%. Median panjang di HTML: ham 3329 (dibawa hard_ham, median 3823), spam 1007, phishing 1268; bercampur dengan perbedaan subset.
- Prediksi vs hasil: "Re:" , ancaman, aksi spam, selisih antar file, dan rasio huruf besar sesuai. Meleset: awalan "[" (ham 15,5 bukan >= 20; spam 5,2 bukan < 5; phishing 2,8 bukan < 2) dan aksi phishing HTML (51,2 bukan >= 55). Penyebab 2,8% phishing berawalan "[" (phishing1 8,6%, phishing2 6,3%) belum diselidiki.
- Keterbatasan: hanya deskriptif, tanpa ukuran nilai tambah bagi model; daftar kata satu bahasa; ham HTML hanya 142 (124 hard_ham).

## Hasil Tahap 5e-1 (analisis nama header, diagnostik, data train)

- Skrip: src/eda_header_names.py. Hanya NAMA header (kolom header_names) dan angka agregat; isi header tidak dibaca. 126 nama muncul di >= 20 email train. header_names tetap hanya diagnostik, BUKAN fitur model.
- `status`: 100,0% phishing (100,0% di tiap file Nazario besar), 0,0% ham, 0,0% spam. Satu-satunya nama yang memenuhi kriteria kandidat terkunci (>= 90% phishing, < 20% ham dan < 20% spam). Dugaan (BELUM diverifikasi): header Status ditambahkan program surat atau sistem penyimpan saat menulis ke mbox, jadi penanda korpus. Menurut konstruksi, n_headers ikut menghitungnya (hipotesis, belum diuji).
- Nama lain yang nol di ham dan spam tetapi ada di phishing: x-original-to 82,2% (per file 100,0/99,6/100,0/65,9), x-uid 73,8% (99,6/99,6/52,2/76,3), lines dan content-length 24,1% (0,0/46,1/1,7/35,0), x-status 86,5% (ham 0,6, spam 6,5), x-spam-level 15,8% dan x-spam-status 15,5% (x-spam-status per file 0,8/56,6/21,4/6,3). Selisih antar file besar, jadi header juga mengenali file/era Nazario.
- Header milis paling "ham": precedence 75,2% ham vs 0,8% phishing, list-id 70,6% vs 0,1%, x-mailman-version 69,8% vs 0,1%. Header utas: in-reply-to 46,1% ham, 0,0% spam, 1,0% phishing; references 36,3%, 0,0%, 1,1% (selaras dengan "Re:" di 5d-6).
- Lantai header (min n_headers / min n_unique): phishing0 16/14, phishing1 6/6, phishing2 14/13, phishing3 16/12; spam 10/8 dan 9/6; ham 6/6 dan 9/7. Setelah status dibuang, min n_unique phishing 13/5/12/11. Median n_unique: ham 23, spam 13, phishing 19 (18 tanpa status). Selisih phishing-spam 6,0 -> 5,0 (menyusut 17%).
- Prediksi vs hasil: kandidat >= 1 nama, selisih antar file >= 30 poin, dan header milis paling ham sesuai. Prediksi "selisih menyusut >= 50%" meleset (17%) karena kandidat hanya satu nama. Perhitungan kasar (rata-rata lima nama kandidat luas = sekitar 3,0 header per email phishing) menunjukkan dampak lebih besar bila semua cap pengumpul dibuang; ini hipotesis setelah melihat hasil, belum diukur.
- Keterbatasan: persen dihitung per kelas di train; asal-usul header (siapa yang menambah) belum diverifikasi; "lantai" n_unique tidak sepenuhnya terjelaskan; tanpa model.

## Hasil Tahap 5e-2 (ablasi cap pengumpul pada n_headers, data train)

- Skrip: src/ablate_header_caps.py. Model dan seed sama dengan artifact_check_shape.py (HistGradientBoosting seed 42, 5 lipatan splits.csv, test tidak disentuh); tiga angka kontrol terproduksi ulang (0,995; 0,979; 0,803). n_headers_adj = n_headers dikurangi jumlah nama cap pada email itu. K1 (terkunci sebelum hasil): status, x-original-to, x-uid, lines, content-length, semua x-spam-\*. K2 (ditentukan setelah melihat tabel 5e-1, eksploratif): K1 + x-status + x-keywords. Batas: n_headers menghitung duplikat nama, header_names hanya nama unik.
- Cap rata-rata per email: phishing K1 3,70, K2 5,56; spam K2 0,37; ham K2 0,01. Median n_headers (asli / K1 / K2): ham 30/30/30; spam 17/17/16; phishing 22/19/17.
- PR-AUC phishing (asli -> K1 -> K2): semua fitur bentuk 0,995 -> 0,982 -> 0,977; kelompok header saja 0,979 -> 0,899 -> 0,843; n_headers sendirian 0,803 -> 0,772 -> 0,710.
- Penafsiran: cap pengumpul menyumbang nyata pada model header, tetapi model bentuk penuh nyaris tidak terganggu (jalan pintas berlapis). Selisih median n_headers phishing vs spam menyusut dari 5 ke 1 setelah K2, jadi "lantai header" sebagian besar terjelaskan oleh keluarga cap tambahan. Asal cap (sistem pengumpul, klien surat, penyimpan mbox) belum diverifikasi.
- Prediksi vs hasil: kontrol sesuai; keempat prediksi lain meleset (penurunan n_headers sendirian jauh lebih kecil dari perkiraan: 0,031 vs >= 0,05; penurunan model header saja lebih besar: 0,080 vs <= 0,03; model penuh turun 0,013 dan 0,018 vs <= 0,01).
- Implikasi untuk Tahap 6: membuang satu kelompok fitur tidak cukup; butuh tolok ukur pengganti. Fitur header dan cap tidak masuk model sungguhan tanpa pembenaran.
- Keterbatasan: satu algoritma dan satu seed; K2 eksploratif; ablasi hanya pada n_headers (nama header tidak dipakai sebagai fitur); angka dari data lama.

## Hasil Tahap 6-1 (ukuran subset sulit, data train, tanpa model)

- Skrip: src/eda_hard_subset.py. Subset didefinisikan dan diukur SEBELUM ada model yang dinilai di dalamnya. H1 = email HTML; H2 = H1 tanpa header milis (has_list_header salah); H3 = H2 tanpa subjek berawalan "Re:" atau "[" (isi subjek tidak dicetak).
- Ukuran (ham / spam / phishing): H1 142 / 789 / 2543; H2 126 / 729 / 2543; H3 121 / 695 / 2460 (H2 = 3,8% / 50,3% / 94,1% dari kelas masing-masing di train).
- H2 per lipatan 0..4 (ham / spam / phishing): 19/145/523, 7/132/502, 6/123/506, 87/140/501, 7/189/511. 69% ham H2 ada di lipatan 3.
- H2 per subset: ham 122 hard_ham + 4 easy_ham_2 + 0 easy_ham; spam 200 (spam) + 529 (spam_2); phishing 19/227/234/712/1351 (20051114, phishing0-3).
- Tumpang tindih n_headers di H2 (ham / spam / phishing): <=13: 86/56/0; 14-17: 19/424/190; 18-21: 7/178/784; 22-25: 7/24/1091; >=26: 7/47/478. 68,3% ham H2 punya n_headers <= 13, tidak satu pun phishing; di rentang n_headers >= 14 hanya 40 ham tersisa.
- Penafsiran: ham di subset sulit hampir seluruhnya hard_ham (96,8%), jadi "ham vs phishing di HTML" praktis = hard_ham vs Nazario, dan pemisahan di rentang n_headers <= 13 tidak memerlukan model sungguhan. Evaluasi phishing vs spam di H2 jauh lebih layak (tumpang tindih lebar), tetapi beda sumber tetap ada. Tidak ada subset yang bersih dari cap pengumpul karena semua phishing memiliki header status.
- Prediksi vs hasil: lipatan, tumpang tindih, dan ukuran ham H3 sesuai; ukuran H2 ham (126 vs 105-125) meleset 1, spam (729 vs 740-789) meleset karena lebih banyak spam punya header milis, penurunan phishing H3 (3,3% vs < 3%) meleset tipis.
- Keterbatasan: belum ada model yang dinilai; ham H2 tidak cukup untuk klaim apa pun tentang false positive pada email sah; butuh sumber ham HTML tambahan (harus saya verifikasi sendiri) atau uji eksternal (Tahap 8).

## Hasil Tahap 6-2 (tolok ukur subset sulit H2, data train)

- Skrip: src/benchmark_h2.py. Enam model dilatih di SELURUH train (OOF 5 lipatan, seed 42), lalu dinilai pada baris H2 (HTML tanpa header milis; ham 126, spam 729, phishing 2543). Kontrol lolos: ukuran H2, ham tumpang tindih (n_headers >= 14) = 40, PR-AUC bentuk HGB 0,995 dan teks 0,994 terproduksi ulang. Acak PR-AUC phishing vs spam di H2 = 0,777. Bentuk dilatih dengan dua algoritma (HGB dan LogReg) supaya selisih fitur tidak tercampur dengan selisih algoritma.
- AUC phishing vs spam di H2 (rentang per lipatan): bentuk HGB 0,993 (0,989-0,997); bentuk LogReg 0,971 (0,954-0,990); link HGB 0,928 (0,921-0,940); teks LogReg 0,996 (0,989-0,998); teks+link 0,994 (0,988-0,997); bentuk+teks+link 0,992 (0,978-1,000). PR-AUC phishing seluruh train: 0,995 / 0,970 / 0,952 / 0,994 / 0,990 / 0,992.
- Selisih berpasangan terhadap bentuk HGB: teks +0,0023 (5 dari 5 lipatan), teks+link +0,0006 (4 dari 5), semua -0,0016 (2 dari 5), bentuk LogReg -0,0219 (0 dari 5); teks+link vs teks -0,0018 (0 dari 5). Aturan terkunci (selisih >= 0,005 dan >= 4 dari 5 lipatan): tidak ada yang mengalahkan bentuk HGB. Kesimpulan: tolok ukur H2 jenuh; tiga jalur berbeda (bentuk, teks, link) memisahkan phishing dari spam hampir sempurna, sehingga benchmark ini tidak bisa membuktikan model sungguhan lebih baik dari jalan pintas. Ketiganya bisa mengenali sumber yang sama (phishing = Nazario, spam = SpamAssassin).
- Pada ambang yang dipilih dari OOF seluruh train agar recall phishing = 90% (hitungan di H2: phishing terdeteksi dari 2543 / spam ditandai dari 729 / ham ditandai dari 126 / ham tumpang ditandai dari 40): bentuk HGB 2379/17/3/3; bentuk LogReg 2356/77/4/4; link 2383/259/18/16; teks 2341/2/1/1; teks+link 2367/12/25/2; semua 2372/8/0/0. Recall di H2 (92,1-93,7%) di atas 90%, berarti phishing di luar H2 (159 email, tanpa HTML) terdeteksi lebih rendah. Perkiraan turunan, bukan pengukuran langsung: sekitar 33% untuk bentuk HGB dan 57% untuk teks (2432 = 0,9 x 2702 dikurangi terdeteksi di H2).
- Temuan: menambah fitur link ke teks tidak menaikkan AUC (-0,0018) tetapi menaikkan ham H2 yang ditandai dari 1 menjadi 25 dari 126 (19,8% vs 0,8%); 23 dari 25 ada di rentang n_headers <= 13. Dugaan (belum diuji): mismatch dan n_links memicu false positive pada email HTML sah ala newsletter (hard_ham mismatch 36,3% di 5c-1).
- Prediksi vs hasil: kontrol, AUC bentuk HGB/teks/link, "tidak ada yang mengalahkan bentuk HGB", dan ham ditandai bentuk (3) sesuai. Meleset: teks+link diprediksi >= teks (hasil -0,0018); semua diprediksi 0,995-0,999 (hasil 0,992); ham ditandai teks diprediksi 3-15 (hasil 1).
- Keterbatasan: ham H2 hanya 126 (96,8% hard_ham, 40 di tumpang tindih), tidak ada klaim umum tentang false positive; satu seed; recall luar-H2 belum diukur langsung; LogReg memakai log1p dan StandardScaler tanpa tuning.

## Riwayat Perubahan

- Tahap 4: rencana awal memakai sender_domain untuk semua kelas diubah menjadi hanya ham/spam, karena hasil eksperimen menunjukkan grup phishing raksasa (40,9%). Keputusan "sender_domain bukan fitur" tidak berubah.
- Setelah Tahap 4: uji artefak awal menunjukkan model hanya-bentuk mencapai PR-AUC phishing 0,995, sehingga tolok ukur Tahap 6 ("model sungguhan harus lebih baik dari model curang") perlu diganti. Penggantinya diputuskan di Tahap 6, bukan sekarang.
- Tahap 5b: kolom diagnostik header_names ditambahkan saat ekstraksi ulang (rencana di bagian "Bedah n_headers" terlaksana); tidak ada keputusan sebelumnya yang diubah.
- Tahap 5c: dua keputusan terbuka ditutup tanpa dikerjakan (pilihan A). (i) Menggabungkan host dari semua salinan duplikat tidak dilakukan: butuh mengubah make_clean_dataset dengan risiko menggeser baris, split, dan grup, sementara fitur angka link sudah stabil antar salinan (5b) dan nilai tambah link kecil (5c-2). (ii) Fitur "domain link vs domain pengirim" tidak dibuat: ia turunan sender_domain yang bukan fitur, dan domain pengirim phishing adalah merek yang dipalsukan. Keduanya dicatat sebagai keterbatasan: fitur berbasis identitas host belum tersedia; fitur_link mengambil host dari salinan pertama untuk duplikat exact. Tidak ada keputusan terkunci yang berubah.
- Tahap 5c: fitur link (kelompok tujuan dan letak) tetap kandidat. Nilai akhirnya dinilai setelah uji artefak di Tahap 6, bukan dari PR-AUC di dalam subset HTML (efek langit-langit di 0,997).
- Tahap 5d: dua uji dari rencana (leave-one-file-out untuk phishing dan ablasi daftar kata artefak) tidak dikerjakan di 5d dan ditunda ke Tahap 6, karena butuh tolok ukur pengganti. Subjek dan kata urgensi baru diukur deskriptif dan belum diputuskan menjadi fitur model. Tidak ada keputusan terkunci yang berubah.
