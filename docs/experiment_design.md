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

## Hasil Tahap 6-3 (ablasi kata sumber ham pada model teks, data train)

- Skrip: src/ablate_words.py. Model teks 5d-2 diulang (Pipeline, seed 42, OOF 5 lipatan) dengan kata dibuang lewat stop_words di dalam TfidfVectorizer. Kontrol baseline lolos: diagonal 3245/1317/2584. W1 (13 kata): listinfo, mailman, wrote, list, spamassassin, razor, newsisfree, xent, freshrpms, rpm, fork, linux, supplied. W2 = W1 + gnupg, pgp. Kontrol acak (15 kata dari kosakata berfrekuensi tinggi, seed 42): appears, encourage, gone, internet, log, mail, registered, removal, sites, space, these, true, websites, would, york.
- Hasil (baseline / W1 / W2 / acak): macro-F1 0,955 / 0,951 / 0,951 / 0,953; PR-AUC phishing 0,994 / 0,993 / 0,993 / 0,994; AUC phishing vs spam di H2 0,996 / 0,995 / 0,995 / 0,996; recall ham 0,987 / 0,988 / 0,988 / 0,986; recall spam 0,910 / 0,903 / 0,903 / 0,910; recall phishing 0,956 / 0,949 / 0,949 / 0,954; ham H2 ditandai pada ambang recall 90%: 1 dari 126 di semua varian.
- Recall ham per subset (baseline / W1 / W2 / acak): easy_ham 0,996 / 0,997 / 0,997 / 0,996; easy_ham_2 0,999 di semua; hard_ham 0,814 / 0,830 / 0,830 / 0,803 (188 email: perubahan hanya 2-3 email, di batas noise). Recall phishing per file (baseline / W1 / W2 / acak): 20051114 0,962 / 0,962 / 0,962 / 0,885 (n=26: 2 email); phishing0 0,859 / 0,851 / 0,851 / 0,847; phishing1 0,978 / 0,981 / 0,981 / 0,978; phishing2 0,945 / 0,935 / 0,937 / 0,945; phishing3 0,976 / 0,967 / 0,967 / 0,974.
- Penafsiran: ketergantungan pada kata sumber ham TIDAK terbukti (recall ham naik 0,001; aturan terkunci: terbukti bila turun >= 0,01 lebih besar daripada kontrol). Kesimpulan: redundan (banyak sinyal lain), bukan "tidak ada jalan pintas". Koefisien tinggi (5d-3) tidak sama dengan ketergantungan. Kluster gnupg (5d-4) tetap terlewat tanpa gnupg dan pgp (recall phishing0 0,851 di W1 dan W2), jadi penyebabnya bukan kata itu saja. Menghapus kata sumber menurunkan recall phishing sekitar 14 email lebih banyak daripada kontrol (0,949 vs 0,954), sebab belum diketahui. Ham yang salah terkonsentrasi di hard_ham: sekitar 35 dari 43 (hitungan turunan).
- KOREKSI atas 5d-3 dan 5d-4: klaim "model mengenali ham lewat footer milis" dan "kluster terlewat karena kata gnupg" tidak didukung ablasi; dianggap hipotesis lemah.
- Prediksi vs hasil: kontrol dan batas PR-AUC/AUC sesuai; recall ham, easy_ham_2, kenaikan recall phishing0, dan stabilitas kontrol di subset kecil meleset.
- Keterbatasan: satu seed dan satu daftar kata; daftar dipilih dari tabel 5d-3 (sudah dilihat); subset kecil (n < 200) hanya petunjuk, batas noise 2-3 email.

## Hasil Tahap 6-4 (leave-one-file-out untuk phishing, data train)

- Skrip: src/lofo_phishing.py. Untuk tiap file Nazario F: latih pada semua baris train kecuali phishing F (ham dan spam ikut), uji pada phishing F saja. Dua model: teks (TF-IDF + LogReg, seperti 5d-2) dan bentuk (HGB, 11 fitur numerik + content_type + charset). Kontrol lolos: diagonal OOF teks 3245/1317/2584. Recall phishing OOF seluruh train: teks 0,956, bentuk 0,967.
- Tumpang tindih: 124 dari 1629 grup phishing (7,6%) muncul di >= 2 file, tetapi grup itu besar: email "bersih" (group_final tidak ada di file lain) hanya 78,2% (phishing0), 44,6% (phishing1), 62,9% (phishing2), 82,5% (phishing3). Seluruh 26 email 20051114 berbagi grup dengan file lain, jadi LOFO-nya tidak bermakna.
- Recall phishing (OOF -> LOFO -> LOFO bersih). Teks: phishing0 0,859 -> 0,819 -> 0,768; phishing1 0,978 -> 0,989 -> 0,975; phishing2 0,945 -> 0,902 -> 0,855; phishing3 0,976 -> 0,816 -> 0,777. Bentuk: phishing0 0,923 -> 0,944 -> 0,928; phishing1 0,959 -> 0,978 -> 0,958; phishing2 0,959 -> 0,909 -> 0,891; phishing3 0,982 -> 0,939 -> 0,942. Kolom OOF dihitung pada semua email file itu, bukan hanya yang bersih.
- Penurunan OOF - LOFO (4 file besar): teks rata-rata 0,058 (berbobot 0,099); bentuk 0,014 (berbobot 0,033). Kesalahan LOFO (ke ham/spam): teks 16/29, 3/0, 45/29, 249/10; bentuk 4/10, 1/5, 9/60, 17/68. Tanpa phishing3 di data latih, model teks menebak 249 dari 259 email phishing3 yang salah sebagai ham.
- Penafsiran (hipotesis): model bentuk tahan terhadap penghapusan satu file karena semua file Nazario membawa penanda koleksi yang sama (status ada di 100% tiap file), jadi LOFO tidak menguji jalan pintas bentuk. Model teks lebih sensitif terhadap pergeseran gaya antar file; phishing3 (52% phishing train) tampak berbeda dari file lain sehingga tanpanya model teks menganggapnya ham. Penyebab perbedaan (era, merek, bahasa) belum diselidiki. Tidak dibuktikan bahwa model teks "lebih jujur".
- Prediksi vs hasil: kontrol, OOF per file, dan grup lintas file < 15% sesuai. Meleset: porsi "bersih" >= 85% (hasil 44,6-82,5%); teks phishing3 >= 0,85 (hasil 0,816); bentuk lebih rapuh daripada teks (hasil sebaliknya).
- Keterbatasan: satu seed; hanya recall kelas positif; n phishing0 248 (galat standar sekitar 2,5 poin); 20051114 (n=26) tidak ditafsirkan; "bersih" dihitung dari group_final (cosine 0,9) sehingga kemiripan di bawah ambang tidak terdeteksi; semua file satu sumber, jadi LOFO bukan bukti generalisasi ke phishing modern.

## Hasil Tahap 6-5 (mengapa phishing3 salah dibaca model teks LOFO, data train)

- Skrip: src/why_phishing3.py. Model teks dilatih tanpa phishing3 (pipeline seperti 5d-2), diuji pada 1404 email phishing3. Kontrol lolos: 249 ke ham dan 10 ke spam (sama dengan 6-4); terdeteksi 1145. Hanya angka agregat, id grup, domain pengirim, dan kata.
- Konsentrasi per group_final: 249 kesalahan ke ham berasal dari 246 grup berbeda; grup teratas 2 kesalahan (0,8%), 3 teratas 6 (2,4%), 5 teratas 8 (3,2%), 10 teratas 13 (5,2%). Kesalahan TIDAK terkonsentrasi di satu kampanye menurut kunci grup teks (cosine 0,9).
- Domain pengirim pada kesalahan (deskriptif, bukan fitur): 53.com 70 (28,1%), bbt.com 70 (28,1%), security.53.com 42 (16,9%), ebay.com 18, bankofamerica.com 8, example.com 5, paypal.com 4, suntrust.com 3; 33 domain berbeda. Tiga domain teratas = 182 email (73,1%); 53.com dan security.53.com digabung 112 (45,0%).
- Kesalahan vs terdeteksi di phishing3: median panjang teks 599 vs 1539 karakter; HTML 95,2% vs 96,6%. Median P(ham) pada kesalahan 0,80; 21,3% punya P(ham) >= 0,9.
- 25 kata yang paling lebih sering di kesalahan daripada di phishing file lain (persen kesalahan / phishing lain / ham): she 44,6/0,3/3,7; his 42,6/1,0/9,2; had 39,8/4,9/16,2; her 30,5/0,4/3,6; him 28,9/0,6/3,3; paul 25,7/0,3/3,0; annie 23,3/0,1/0,0; said 17,7/0,4/12,5; looked 12,4/0,1/2,0; came 11,6/0,6/3,3; hand 11,2/0,2/3,6. Kata-kata ini bergaya teks naratif dan beririsan dengan anomali 5d-3 (annie, paul, kata ganti).
- Penafsiran (HIPOTESIS, belum diverifikasi; isi email tidak dibaca): (1) kunci grup teks (cosine 0,9) tidak menangkap kampanye satu merek: email berbeda tulisan tetapi satu merek tersebar di banyak grup dan kemungkinan ada di lipatan latih dan validasi sekaligus, sejalan dengan temuan 4 (87,2% domain pengirim phishing di test ada di train). (2) Kata naratif mungkin potongan prosa sisipan untuk mengelabui filter. (3) Recall phishing3 0,976 di CV acak sebagian berasal dari pola kampanye yang dipelajari dari phishing3 sendiri. Saat phishing3 ditahan, pola itu hilang dan model menebak ham.
- Prediksi vs hasil: kontrol, domain tunggal >= 20% (28,1%), dan teks lebih pendek sesuai. Meleset: konsentrasi per grup (hasil 246 grup, 3 teratas 2,4%), selisih HTML >= 10 poin (hasil 1,4 poin), median P(ham) < 0,8 (hasil 0,80, tidak terpenuhi).
- Implikasi: menambah alasan uji kepekaan ambang cosine 0,9 dan leave-brand-out di Tahap 8; laporan recall phishing di CV acak bersifat optimis; kunci grup phishing tanpa domain adalah pilihan sadar dengan harga ini.
- Keterbatasan: satu seed; daftar kata bersifat petunjuk (n kesalahan 249, banyak kampanye); persen kata deskriptif di train; hipotesis naratif dan merek-tidak-dikenal belum diuji langsung.

## Hasil Tahap 6-6 (uji hipotesis merek dan kata naratif untuk kesalahan LOFO phishing3, data train)

- Skrip: src/hypo_phishing3.py. Kontrol lolos: OOF 3245/1317/2584; LOFO phishing3 ke ham 249 dan ke spam 10. Daftar 9 kata naratif (she his her him said looked came hand little) dan ambang >= 3 kata dipilih SETELAH melihat tabel 6-5, jadi uji kata bersifat eksploratif. TOP3 = 53.com, bbt.com, security.53.com.
- Merek: TOP3 digabung 209 email di phishing3 (207 group_final berbeda: hampir satu grup per email), hanya 3 email di file phishing lain dan 0 di ham/spam. Recall OOF 0,943 vs LOFO 0,129 (182 dari 209 salah). Per domain (n / OOF / LOFO): 53.com 77/0,961/0,091; bbt.com 85/0,953/0,176; security.53.com 47/0,894/0,106. Domain lain di phishing3 (n=1195): OOF 0,982, LOFO 0,936. Pembanding (n di phishing3 / n di file lain / OOF / LOFO): ebay.com 254/176/0,972/0,929; paypal.com 232/278/1,000/0,983; bankofamerica.com 37/1/0,973/0,784; suntrust.com 16/3/0,875/0,812.
- Kata naratif (persen email dengan >= 3 dari 9 kata): phishing3 domain TOP3 45,0% (n=209); phishing3 domain lain 1,6% (n=1195); phishing file lain 0,5% (n=1298); ham 4,3% (n=3288); spam 3,2% (n=1448). Recall phishing3 (n / OOF / LOFO): TOP3+flag 94/0,957/0,000; TOP3 tanpa flag 115/0,930/0,235; domain lain+flag 19/0,789/0,158; domain lain tanpa flag 1176/0,985/0,948.
- Kesalahan LOFO phishing3 (n=259): 182 (70,3%) di domain TOP3; 110 (42,5%) bertanda naratif; TOP3 atau naratif 198; tidak terjelaskan 61 (bukan TOP3 dan tanpa flag; 5,2% dari 1176 email domain-lain-tanpa-flag).
- Penafsiran (hipotesis): recall CV acak pada TOP3 tinggi walau hampir tiap email punya group_final sendiri, sedangkan recall LOFO rendah. Ini konsisten dengan kebocoran tingkat merek atau templat: kunci grup teks (cosine 0,9) tidak menyatukan email dari satu merek, mungkin karena teks sisipan naratif membuat teks tiap email berbeda (belum diverifikasi langsung). Recall tinggi pada merek yang umum di file lain (ebay, paypal) dan rendah pada tiga domain bank regional; namun bankofamerica (1 di file lain) dan suntrust (3) tetap sekitar 0,8, jadi "merek asing" saja tidak cukup menjelaskan.
- Implikasi: recall phishing di CV acak berpotensi optimis untuk merek yang sudah terlihat di data latih, dan recall untuk merek atau templat baru bisa sangat rendah (TOP3 0,129). Di Tahap 8 laporkan hasil per merek (leave-brand-out) dan uji kepekaan ambang cosine 0,9. splits.csv tidak diubah.
- Prediksi vs hasil: kontrol, LOFO TOP3 <= 0,40 (0,129), kemunculan TOP3 di tempat lain <= 10 (3), dan prevalensi flag di ham/spam/phishing lain sesuai. Meleset: recall OOF TOP3 >= 0,95 (0,943, tipis); flag di kesalahan >= 50% (42,5%); tidak terjelaskan <= 30 (61).
- Keterbatasan: daftar kata dan ambang eksploratif; satu seed dan satu model; sel kecil (n=16 sampai 47 per domain; domain lain+flag n=19); asal-usul teks naratif tidak diperiksa; hanya data train.

## Kesimpulan Tahap 6 (tolok ukur pengganti dan uji artefak; data train)

- Tujuan tahap: membuktikan model sungguhan memberi nilai di luar jalan pintas. Hasil: TIDAK dapat dibuktikan dari data internal ini, karena semua phishing berasal dari satu sumber (Nazario; header status ada di 100% phishing dan 0% ham dan spam) dan semua pembanding berasal dari sumber lain.
- Benchmark H2 (HTML tanpa header milis; ham 126, spam 729, phishing 2543) jenuh: AUC phishing vs spam bentuk HGB 0,993, teks 0,996, link 0,928; tidak ada model yang mengalahkan bentuk menurut aturan terkunci (selisih >= 0,005 dan membaik di >= 4 dari 5 lipatan). Ham di H2 96,8% hard_ham dan hanya 40 yang tumpang tindih, jadi tidak ada klaim false positive ham dari data ini.
- Ablasi kata sumber ham (13 dan 15 kata, kontrol 15 kata acak): recall ham tidak turun (0,987 ke 0,988). Model teks redundan, bukan terbukti bergantung pada kata itu; klaim 5d-3 dan 5d-4 dikoreksi.
- LOFO (satu file Nazario ditahan): penurunan recall teks rata-rata 0,058 (berbobot 0,099; phishing3 0,976 ke 0,816), bentuk 0,014. Bentuk tahan karena semua file membawa penanda koleksi yang sama, jadi LOFO tidak menguji jalan pintas bentuk.
- Kebocoran tingkat merek atau templat: tiga domain bank (209 email di phishing3 dalam 207 grup) punya recall OOF 0,943 tetapi LOFO 0,129. Kunci grup teks (cosine 0,9) tidak menangkap merek, jadi recall CV acak optimis untuk merek yang sudah terlihat. Leave-brand-out dan uji kepekaan cosine dikerjakan di Tahap 8; splits.csv tidak diubah.
- Status: Tahap 6 selesai. Bukti nilai tambah di luar jalan pintas ditunda ke Tahap 8 (leave-brand-out, MeAJOR, phishing modern 2015-2025 lewat Docker). Fitur bentuk dan header dipertahankan sebagai pembanding "model curang", bukan otomatis fitur model.

## Hasil Tahap 7-1 (baseline teks-saja dan ambang dari OOF, data train)

- Skrip: src/baseline_text.py. Pipeline sama dengan cv_text.py (TF-IDF di dalam Pipeline + LogReg seed 42), 5 lipatan splits.csv, test dibuang di awal. Kontrol lolos: diagonal 3245/1317/2584, 2702 phishing dalam 1629 grup. Aturan: phishing bila P(phishing) >= ambang, selain itu tebakan terbanyak antara ham dan spam; ambang = nilai tertinggi yang masih memberi recall OOF >= target.
- Hasil untuk target 0,90 / 0,93 / 0,95: ambang 0,5593 / 0,5040 / 0,4496; recall email 0,900 / 0,930 / 0,950; recall grup 0,862 / 0,908 / 0,937; precision 0,996 (2432/2442) / 0,986 (2513/2549) / 0,982 (2567/2614); salah tangkap ham/spam 4/6, 5/31, 8/39; macro-F1 0,940 / 0,948 / 0,954; recall per lipatan 0,881-0,915 / 0,900-0,948 / 0,937-0,965.
- Keputusan (opsi B): ambang resmi = target recall OOF 0,93 (ambang 0,5040). Alasan: pada target 0,90 satu lipatan sudah 0,881 di sampel yang dipakai memilih ambang, dan LOFO menunjukkan recall untuk merek baru bisa jauh lebih rendah. Syarat recall >= 90% tidak berubah. Harga: dari 0,90 ke 0,93 didapat +81 phishing tertangkap dan +26 salah tangkap (25 spam, 1 ham).
- Penafsiran (hipotesis, belum diuji): recall grup lebih rendah daripada recall email (selisih 0,038 / 0,022 / 0,013) karena grup tunggal (1281 dari 1629 grup, recall lebih rendah di 5d-5) berbobot sama dengan grup besar.
- Keterbatasan: ambang dipilih dan dinilai pada OOF yang sama (optimis, batas atas); satu model dan satu seed; sekitar 540 phishing per lipatan (galat standar sekitar 1 poin); LogReg belum di-tuning dan belum dikalibrasi; precision pada prevalensi realistis belum diestimasi.

## Hasil Tahap 7-2 dan 7-3 (perbandingan klasifier dan leave-one-brand-out, data train)

- Skrip: src/compare_models.py (LogReg vs RandomForest 300 pohon seed 42; TF-IDF dan 5 lipatan identik; ambang resmi = target recall OOF 0,93) dan src/lobo_brand.py (tiap merek phishing dengan >= 30 email ditahan, grup teks yang sama ikut dibuang dari data latih). Kontrol lolos: diagonal 3245/1317/2584; ambang LogReg 0,5040; LOFO phishing3 249 ke ham, 10 ke spam, 1145 terdeteksi.
- 7-2: PR-AUC phishing LogReg 0,994 (lipatan 0,990-0,997) vs RF 0,992 (0,985-0,996); macro-F1 argmax 0,955 vs 0,936; pada recall 0,93 precision 0,986 (2513/2549, salah tangkap ham/spam 5/31) vs 0,981 (2514/2563, 8/41). Selisih PR-AUC per lipatan -0,0042 / -0,0042 / +0,0006 / -0,0031 / -0,0005 (rata-rata -0,0023, membaik 1 dari 5): aturan terkunci tidak terpenuhi, selisih dalam noise. LogReg tetap baseline.
- 7-3 (eksploratif; 16 merek, n=1689; recall pada ambang resmi, OOF -> LOBO): gabungan LogReg 0,972 -> 0,939, RF 0,964 -> 0,918. Sebelas merek tidak berubah (sembilan di 1,000, jenuh). Turun: 53.com 0,924 -> 0,443 (n=79), security.53.com 0,830 -> 0,766 (n=47), bbt.com 0,919 -> 0,837 (n=86), paypal.com 0,994 -> 0,990 (n=510), ebay.com 0,949 -> 0,937 (n=430). RF lebih rendah di LOBO gabungan (selisih 0,021), terutama di security.53.com (0,298 vs 0,766).
- Penafsiran (hipotesis, belum diuji): menahan satu merek tidak meruntuhkan recall seperti LOFO phishing3 di 6-6 (53.com / bbt.com / security.53.com 0,091 / 0,176 / 0,106 -> 0,443 / 0,837 / 0,766), jadi sebagian keruntuhan 6-6 mungkin berasal dari hilangnya sisa file phishing3 (gaya atau kit yang dipakai bersama), bukan hanya merek. Rata-rata gabungan 0,939 ditopang merek besar dan merek yang jenuh; kelemahan terkonsentrasi di tiga domain bank.
- Keterbatasan: uji eksploratif (daftar merek dari ukuran di train, aturan tetap sebelum hasil); purge hanya memakai group_final (cosine 0,9), sehingga kit lintas merek dengan teks berbeda tetap bocor (angka LOBO = batas atas); subdomain (paypal.com, intl.paypal.com, email.paypal.com) dihitung sebagai merek terpisah; hanya recall, tanpa false positive; sel kecil (n 32-86 untuk 14 merek); satu seed.

## Hasil Tahap 7-4 (tuning C LogReg teks-saja: CV, LOBO, dan tiga bank ditahan bersamaan, data train)

- Skrip: src/tune_c.py. Satu perubahan: C (0,1 / 0,3 / 1 / 3 / 10 / 30); fitur, lipatan, dan cara ambang (target recall OOF 0,93, dihitung ulang per C) tetap. Aturan dikunci sebelum hasil: C diganti hanya jika precision naik >= 0,005, LOBO16 tidak turun > 0,01, dan tanpa peringatan konvergensi. Kontrol C=1 lolos (ambang 0,5040; 2513/2549; LOBO16 1586/1689). Tiga bank gabungan (212 email) adalah uji eksploratif yang dipilih setelah 7-3.
- Hasil (C: PR-AUC / precision pada recall 0,93 / LOBO16): 0,1: 0,988 / 0,952 (2526/2652) / 0,910; 0,3: 0,993 / 0,980 (2513/2565) / 0,937; 1: 0,994 / 0,986 (2513/2549) / 0,939; 3: 0,995 / 0,987 (2513/2547) / 0,944; 10: 0,995 / 0,989 (2516/2545) / 0,939; 30: 0,995 / 0,989 (2514/2543) / 0,936. Tidak ada peringatan konvergensi. Tidak ada kandidat yang memenuhi aturan (kenaikan precision terbesar +0,003), jadi C=1 dipertahankan.
- Tiga bank (53.com, bbt.com, security.53.com) ditahan bersamaan, recall pada ambang tiap C: 0,236 / 0,241 / 0,245 / 0,269 / 0,325 / 0,349 untuk C 0,1 sampai 30; 53.com sendiri 0,253 sampai 0,468. Pada C=1 gabungan 0,245 vs sekitar 0,675 bila satu per satu (rata-rata berbobot dari angka bulat 7-3).
- Penafsiran (hipotesis, belum diuji): bank saudara di data latih membawa pola yang membantu saat satu bank ditahan, jadi yang bocor di CV acak kemungkinan keluarga merek atau kit, bukan satu merek. Kenaikan pelan terhadap C pada tiga bank tidak dipakai memilih C (post hoc, satu keluarga, ambang berbeda per C). Pada C=0,1 tp 2526 > 2513 kemungkinan karena skor sama (ties); belum diperiksa.
- Keterbatasan: tuning dan penilaian memakai data yang sama (bukan kinerja akhir; penilaian akhir hanya dari test di Tahap 8); selisih antar C >= 1 dalam noise (salah tangkap 36 vs 29 dari sekitar 2545); satu seed; tiga bank = satu keluarga, n=212; hanya recall di LOBO.

## Kesimpulan Tahap 7 (baseline dan perbandingan model teks-saja; data train)

- Model kandidat: TF-IDF body_text + LogReg C=1 (seed 42), ambang 0,5040 dari target recall OOF 0,93 (opsi B, 7-1). Di OOF train: recall email 0,930, recall grup 0,908, precision 0,986 (2513/2549), salah tangkap ham/spam 5/31, PR-AUC 0,994, macro-F1 argmax 0,955, recall per lipatan 0,900-0,948. Ini batas atas karena ambang dipilih dan dinilai pada OOF yang sama.
- Pembanding: RandomForest tidak lebih baik (PR-AUC 0,992 vs 0,994, membaik 1 dari 5 lipatan; aturan terkunci tidak terpenuhi). Tuning C (0,1 sampai 30) tidak menghasilkan kandidat menurut aturan terkunci, jadi C=1 dipertahankan. Beberapa seed untuk RF dilewati: LogReg deterministik dan RF kalah di 4 dari 5 lipatan, jadi variasi seed kecil kemungkinan membalik keputusan (belum diukur).
- Uji merek (eksploratif): leave-one-brand-out dengan purge pada 16 merek: recall 0,972 (OOF) -> 0,939 (LOBO); terkonsentrasi di tiga bank (53.com 0,443; bbt.com 0,837; security.53.com 0,766). Tiga bank ditahan bersamaan: 0,245. Hipotesis (belum diuji): yang bocor di CV acak adalah keluarga merek atau kit, bukan satu merek.
- Status: model belum disentuh test set. Bukti nilai tambah di luar jalan pintas belum ada (satu sumber phishing). Untuk Tahap 8: putuskan apakah ambang 0,5040 (dari model yang dilatih 80% train) dipakai langsung pada model yang dilatih 100% train; wajib uji kepekaan, kalibrasi, estimasi precision pada prevalensi realistis, MeAJOR, phishing modern, dan ablasi link.
- Keterbatasan: satu seed dan satu arsitektur fitur (teks saja); tuning dan penilaian di data yang sama; 9 dari 16 merek LOBO jenuh di 1,000; skrip 7-1 sampai 7-4 menyalin kode pemuat data (dirapikan di Tahap 13).

## Rencana Tahap 8-0 (dikunci sebelum hasil; tanpa test)

- Model akhir (opsi A): TF-IDF body_text + LogReg C=1 seed 42, dilatih di 100% train; ambang tetap 0,5040 (target recall OOF 0,93, 7-1), tidak disetel ulang di test. Kalibrasi (monoton, tidak mengubah keputusan) dipindah ke Tahap 9-10 untuk skor Low/Medium/High.
- Cek pergeseran skala ambang (src/shift_check.py, data train): model 60% vs 80% data latih pada ambang tetap. Prediksi: selisih recall <= 0,02, lebih rendah di 60%. Aturan: |recall80 - rata-rata recall60| <= 0,02 maka A; lebih besar maka B (rata-rata 5 model lipatan). Batas: ekstrapolasi 60->80 ke 100% hanya perkiraan kasar.
- Aturan 8-2 (link masuk model akhir hanya bila SEMUA terpenuhi): precision pada recall 0,93 naik >= 0,005; LOBO16 tidak turun > 0,01; salah tangkap ham tidak bertambah > 5 email. Selain itu model tetap teks-saja.
- Hasil 8-3 (MeAJOR) dan 8-4 (phishing modern) tidak boleh mengubah model atau ambang; dilaporkan apa adanya.
- Prediksi 8-5 (pada ambang 0,5040, tentatif): recall phishing 0,89-0,95 (galat standar n=676 sekitar 0,010), precision 0,96-0,99, PR-AUC >= 0,99. PR-AUC >= 0,99 sudah dipastikan oleh jalan pintas sumber (model bentuk 0,995), jadi test TIDAK bisa menepis kecurigaan kebocoran. Target >= 0,90 terpenuhi bila estimasi titik >= 0,90; interval Wilson dilaporkan; skrip test dijalankan SEKALI.
- Koreksi tertunda: "87,2% (424 dari 504 = 84,1%)" di dua tempat di dokumen ini belum dihitung ulang karena butuh domain email test; dihitung di 8-5. Sampai itu, angka 87,2% belum dapat dipercaya.

## Hasil Tahap 8-0 (cek pergeseran skala ambang, data train)

- Skrip: src/shift_check.py. Kontrol lolos (diagonal 3245/1317/2584, ambang 0,5040, tp 2513). Pada ambang tetap 0,5040, model dengan 80% data latih: recall 0,930, precision 0,986 (2513/2549), median P pada phishing 0,976; model 60% (4 putaran): recall 0,909-0,910, precision 0,989-0,992 (2457-2460 dari 2478-2487), median P 0,969.
- Selisih recall 80% - rata-rata 60% = 55/2702 = +0,0204 (tercetak +0,020 karena pembulatan), di atas batas terkunci 0,02, jadi aturan memilih B: model akhir = rata-rata P(phishing) dari 5 model lipatan, ambang 0,5040. Prediksi meleset tipis (diprediksi <= 0,02); batas tidak dilonggarkan.
- Penafsiran (hipotesis, belum diuji): model dengan data lebih banyak lebih yakin dan menandai lebih banyak email, jadi di 100% data recall pada ambang tetap kemungkinan >= 0,93 dengan precision lebih rendah. B menjaga tiap anggota di 80% data (sama dengan OOF), tetapi skala rata-rata 5 model belum diukur.
- Keterbatasan: ekstrapolasi 60% ke 80% ke 100% hanya perkiraan; satu seed; ambang dan penilaian dari OOF yang sama; B tidak punya cek skala sendiri; Tahap 9-10 harus membawa 5 model (kosakata berbeda per lipatan). Di 8-5 model 100% (A) boleh dilaporkan sebagai diagnostik pada satu kali jalan yang sama, tanpa dipakai memilih.
- Koreksi pembacaan (dari kode make_splits.py, angka belum dihitung ulang): satuan "87,2%" dan "424 dari 504" di dokumen ini adalah EMAIL phishing test, bukan domain. 87,2% = email berdomain yang domainnya ada di train (semua domain); 424 dari 504 = hanya email berdomain layak (bukan generik/jembatan) = 84,1%. Dua penyebut berbeda, bukan konflik angka.

## Rencana Tahap 8-1 (uji kepekaan split; dikunci sebelum hasil; data train)

- Skrip src/sensitivity_split.py. Skenario, masing-masing mengubah SATU hal dari split resmi: S0 resmi (kontrol); R1 dan R2 = grup resmi dengan seed lipatan 43 dan 44 (ukuran noise undian lipatan); C08 dan C07 = ambang cosine 0,8 dan 0,7; J10 dan J02 = batas grup ham terbesar 10% dan 2% lewat jalur greedy jembatan (jalur 5% harus menghasilkan 5 jembatan resmi). Model tetap TF-IDF + LogReg C=1; test tidak dipakai untuk model.
- Metrik dan aturan: PR-AUC phishing dan precision pada recall OOF 0,93 (ambang dihitung ulang per skenario). Noise = selisih terbesar |R1/R2 - S0|. Skenario PEKA bila |selisih| >= max(0,005; 2 x noise) pada salah satu metrik. Bila grup terbesar suatu kelas > 15% dari kelas itu di train: ditandai GRUP BESAR, dilaporkan tetapi tidak ditafsirkan. Bila lipatan atau model gagal dibentuk: dilaporkan sebagai temuan.
- Prediksi: kontrol S0 = PR-AUC 0,994, macro-F1 0,955, 2513/2549. Noise |dPR-AUC| <= 0,002 dan |dPrecision| <= 0,006. C08 dan C07 lebih rendah (PR-AUC -0,001 sampai -0,006; precision -0,002 sampai -0,02; C07 paling besar bila hipotesis keluarga merek/kit benar). J10 dan J02 tidak peka.
- Tafsir: bila C08/C07 PEKA dan lebih rendah, angka OOF resmi adalah batas atas sebesar selisih itu. Bila tidak peka, split tahan terhadap pilihan ini untuk model teks, BUKAN bukti tidak ada kebocoran keluarga atau kit.
- Batas: teks test ikut membangun graf grup (struktural, seperti produksi; Kontrol 1 membuktikan hasilnya identik); noise hanya dari dua seed; kemiripan train-test di bawah cosine 0,9 tidak diuji (ditunda ke 8-5, diagnostik agregat); pemilihan jembatan alternatif (mis. berdasar jumlah email) tidak diuji.

## Hasil Tahap 8-1 (uji kepekaan split, data train)

- Skrip src/sensitivity_split.py; Kontrol 1-3 lolos (group_id, group_final, lipatan resmi, dan OOF 7-1 terproduksi ulang; jalur greedy: 2/5/10 jembatan untuk batas grup ham 10%/5%/2%). Grup resmi di train: 3809.
- PR-AUC / precision pada recall OOF 0,93: S0 0,9941 / 0,986; noise seed lipatan (R1, R2) <= 0,0001 / <= 0,0008; C08 (cosine 0,8) 0,9935 / 0,984; C07 (cosine 0,7; grup ham terbesar 14,6%) 0,9931 / 0,983; J10 0,9939 / 0,985; J02 0,9939 / 0,985. Semua skenario tidak peka (batas 0,005). Prediksi benar untuk noise dan J10/J02; C08 turun lebih kecil dari prediksi (-0,0006 / -0,0015).
- Penafsiran (hipotesis): OOF model teks tahan terhadap pengetatan grup berbasis kemiripan teks sampai cosine 0,7 dan terhadap 2-10 jembatan, jadi kebocoran near-duplicate bukan penyebab utama angka tinggi. Ini TIDAK menyentuh kebocoran tingkat merek/kit (LOBO 7-3 dan 7-4 tetap temuan terpisah).
- Eksploratif (di luar aturan terkunci): ambang recall 0,93 bergeser turun makin ketat grupnya (0,5040; C08 0,4978; C07 0,4889; rentang antar seed 0,5006-0,5061), jadi ambang tetap 0,5040 bisa memberi recall < 0,93 pada data yang lebih asing; belum diukur karena recall pada ambang tetap tidak dicetak. Macro-F1 lebih berisik (0,950-0,955 antar seed; C07 0,946) dan tidak masuk aturan. tp 2514-2524 > 2513 pada R1, C08, J02 kemungkinan skor sama (ties), belum diperiksa.
- Batas: noise hanya dari dua seed; satu model (teks + LogReg C=1); metrik berfokus phishing sehingga efek jembatan pada ham/spam kurang terlihat; kemiripan train-test di bawah cosine 0,9 ditunda ke 8-5; pemilihan jembatan alternatif tidak diuji.

## Riwayat Perubahan

- Tahap 4: rencana awal memakai sender_domain untuk semua kelas diubah menjadi hanya ham/spam, karena hasil eksperimen menunjukkan grup phishing raksasa (40,9%). Keputusan "sender_domain bukan fitur" tidak berubah.
- Setelah Tahap 4: uji artefak awal menunjukkan model hanya-bentuk mencapai PR-AUC phishing 0,995, sehingga tolok ukur Tahap 6 ("model sungguhan harus lebih baik dari model curang") perlu diganti. Penggantinya diputuskan di Tahap 6, bukan sekarang.
- Tahap 5b: kolom diagnostik header_names ditambahkan saat ekstraksi ulang (rencana di bagian "Bedah n_headers" terlaksana); tidak ada keputusan sebelumnya yang diubah.
- Tahap 5c: dua keputusan terbuka ditutup tanpa dikerjakan (pilihan A). (i) Menggabungkan host dari semua salinan duplikat tidak dilakukan: butuh mengubah make_clean_dataset dengan risiko menggeser baris, split, dan grup, sementara fitur angka link sudah stabil antar salinan (5b) dan nilai tambah link kecil (5c-2). (ii) Fitur "domain link vs domain pengirim" tidak dibuat: ia turunan sender_domain yang bukan fitur, dan domain pengirim phishing adalah merek yang dipalsukan. Keduanya dicatat sebagai keterbatasan: fitur berbasis identitas host belum tersedia; fitur_link mengambil host dari salinan pertama untuk duplikat exact. Tidak ada keputusan terkunci yang berubah.
- Tahap 5c: fitur link (kelompok tujuan dan letak) tetap kandidat. Nilai akhirnya dinilai setelah uji artefak di Tahap 6, bukan dari PR-AUC di dalam subset HTML (efek langit-langit di 0,997).
- Tahap 5d: dua uji dari rencana (leave-one-file-out untuk phishing dan ablasi daftar kata artefak) tidak dikerjakan di 5d dan ditunda ke Tahap 6, karena butuh tolok ukur pengganti. Subjek dan kata urgensi baru diukur deskriptif dan belum diputuskan menjadi fitur model. Tidak ada keputusan terkunci yang berubah.
- Tahap 7-1: syarat recall phishing >= 90% diterapkan sebagai target recall OOF 0,93 (bukan 0,90 pas), karena satu lipatan jatuh ke 0,881 pada target 0,90 dan LOFO menunjukkan CV acak optimis. Syarat terkunci tidak berubah; precision tetap dimaksimalkan di bawah syarat itu.
- Tahap 7-3: CV alternatif berbasis merek dengan grup phishing = domain + teks tidak dibuat (akan menciptakan grup raksasa 40,9% seperti di Tahap 4); diganti leave-one-brand-out dengan purge, dihitung di memori, splits.csv tidak diubah. Label "kebocoran tingkat merek" di 6-6 diturunkan menjadi hipotesis "kebocoran tingkat kit atau file" sampai diuji (menahan satu merek: 53.com 0,443, bbt.com 0,837, security.53.com 0,766, vs LOFO 6-6: 0,091 / 0,176 / 0,106). 7-2: RF tidak mengalahkan LogReg (aturan terkunci tidak terpenuhi).
- Tahap 7-4: C=1 dipertahankan (tidak ada C yang memenuhi aturan terkunci). Hipotesis "kit atau file" dari 7-3 dipersempit: tiga bank ditahan bersamaan memberi recall 0,245 (vs sekitar 0,675 satu per satu), jadi yang bocor kemungkinan keluarga merek atau kit. Usulan untuk Tahap 8 (belum diputuskan): uji kepekaan dengan ambang cosine lebih rendah sebagai pendekatan kasar untuk menyatukan keluarga.
- Tahap 8-0: opsi A (model 100% train, ambang 0,5040 apa adanya) diganti B (rata-rata 5 model lipatan) karena cek pergeseran memberi selisih recall 0,0204 > batas terkunci 0,02. Pembacaan 87,2% vs 424/504 dikoreksi (satuan email, dua penyebut).
