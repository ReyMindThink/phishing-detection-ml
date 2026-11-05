# Model card: detektor phishing berbasis teks (TF-IDF + regresi logistik)

Kartu ini menjelaskan apa yang dikerjakan model, apa yang TIDAK terbukti, dan bagaimana memuatnya dengan benar. Penunjuk seperti [Hasil 8-5] mengarah ke bagian bernama itu di [docs/experiment_design.md](experiment_design.md); label **eksploratif** dan **hipotesis** dijelaskan di [README](../README.md). Ini model edukasi, bukan produk.

## Ringkasan model

- **Jenis:** rata-rata 5 model lipatan. Tiap model = TF-IDF pada `body_text` (token huruf minimal 3, min_df 3, maksimum 20000 fitur, sublinear_tf) + regresi logistik multinomial (C=1, max_iter 1000, seed 42). Hanya teks; tidak ada fitur link, header, atau domain pengirim [Hasil 8-2; Kesimpulan 8].
- **Masukan:** teks isi email hasil parser (`body_text`), bukan HTML mentah dan bukan lampiran.
- **Keluaran:** skor = rata-rata P(phishing) dari 5 model. Skor BUKAN probabilitas terkalibrasi [Hasil 8-5].
- **Putusan:** phishing bila skor mencapai ambang 0,5039704393178396 (target recall 0,93 pada data latih); selain itu kelas ham atau spam dengan P rata-rata terbesar [Kesimpulan 7; Hasil 8-5].
- **Pelatihan:** tiap model dilatih pada sekitar 80% data latih (5950 atau 5951 email menurut [manifest](model_manifest.json)), lima lipatan, tanpa tuning lanjutan sesudah test dibuka. Model 100% data tidak dilatih [Kesimpulan 8].

## Penggunaan yang dimaksud

- Belajar dan mendemonstrasikan cara mengevaluasi detektor phishing, termasuk jalan pintas dataset dan batas klaim.
- Demo lokal: aplikasi di repo ini menampilkan skor, pita risiko, dan status "tidak dapat dinilai".

## Di luar cakupan (jangan dipakai untuk)

- Filter email produksi atau keputusan keamanan otomatis; model ini tidak untuk menjadi satu-satunya dasar menilai email.
- Menyimpulkan bahwa sebuah email "aman" dari skor rendah, pita LOW, atau status "tidak dapat dinilai". Status itu berarti model tidak punya dasar, bukan aman [Hasil 9-4].
- Email berbahasa selain Inggris, email yang hanya berisi gambar atau tautan, atau teks sangat pendek.
- Phishing terarah atau serangan yang sengaja disusun untuk menghindari model: tidak diuji.
- Penerbitan publik sebagai layanan: tidak ada autentikasi, pembatasan laju, atau penyimpanan aman [docs/security_checklist.md](security_checklist.md).

## Data

- **Latih:** 7438 email (ham 3288, spam 1448, phishing 2702) dari dua sumber: ham dan spam dari SpamAssassin Public Corpus (set 20030228), phishing klasik dari korpus Nazario (2002-2007) [Hasil 9-3c; Kesimpulan 8]. **Test:** 1860 email (ham 822, spam 362, phishing 676) dari sumber yang sama, dibuka sekali [Hasil 8-5].
- **Eksternal (hanya uji):** phishing modern 2015-2025 dari pengumpul Nazario yang sama, dan MeAJOR (format anonim) [Hasil 8-4-2; Hasil 8-3-2].
- Pemisahan latih dan test memakai grup near-duplicate (kemiripan kosinus 0,9); tetap 54 dari 1860 email test (2,9%) punya kembaran isi di data latih [Hasil 8-5].
- Data mentah tidak disertakan. Asal, lisensi, dan batas ada di [SOURCES.md](../SOURCES.md) dan [NOTICE](../NOTICE).

## Metrik, dan berlaku untuk apa

| Ukuran                               | Nilai                                                   | Berlaku untuk                                        | Penunjuk     |
| ------------------------------------ | ------------------------------------------------------- | ---------------------------------------------------- | ------------ |
| Test internal, phishing              | recall 0,9467 (Wilson 0,927-0,961); precision 0,9816    | n=1860; sumber sama dengan latih; optimistis         | Hasil 8-5    |
| Test internal, keseluruhan           | macro-F1 0,9535; akurasi 0,9586; PR-AUC phishing 0,9967 | idem                                                 | Hasil 8-5    |
| Test, per kelas (precision / recall) | ham 0,9528 / 0,9818; spam 0,9307 / 0,9282               | idem                                                 | Hasil 8-5    |
| Merek ditahan (LOBO16)               | recall 0,939                                            | data latih, 16 merek; eksploratif                    | Kesimpulan 7 |
| Tiga bank ditahan bersamaan          | recall 0,245                                            | data latih; eksploratif                              | Hasil 7-4    |
| Phishing modern 2015-2025            | recall 0,7919 (Wilson 0,777-0,806)                      | 3075 email unik, satu pengumpul; hanya recall        | Hasil 8-4-2  |
| MeAJOR label 0                       | 4,28% ditandai phishing                                 | 60648 email, format anonim; penyebab tak terpisahkan | Hasil 8-3-2  |
| Precision indikatif                  | 0,486 pada prevalensi 1%; 0,831 pada 5%                 | dari tingkat salah tangkap test 0,0101               | Hasil 8-5    |

Angka test tinggi konsisten dengan jalan pintas sumber (model yang hanya melihat bentuk email mencapai PR-AUC 0,995), jadi ia tidak membuktikan kemampuan di dunia nyata [Hasil Uji Artefak Awal; Kesimpulan 8].

## Risiko dan keterbatasan

- **Rasa aman palsu (risiko utama).** Pada phishing modern, sekitar 1 dari 5 lolos dari ambang (recall 0,7919, hitungan turunan), dan yang lolos lebih sering diputuskan ham (14,8%) daripada spam (6,0%) [Hasil 8-4-2]. Pita LOW pada validasi silang data latih masih memuat 27 phishing dari 4374 (0,6%), dan pita itu indikatif [Hasil 9-3].
- **Pita MEDIUM lebar.** MEDIUM berisi 31,5% phishing pada data latih; baca sebagai "perlu diperiksa", bukan "kemungkinan phishing" [Hasil 9-3; Hasil 9-4].
- **Teks kosong atau tanpa kata dikenal dinilai phishing** (skor 0,5158), sehingga aplikasi memakai gerbang. Gerbang v2 dirancang setelah melihat hasil, hanya mengukur kosakata Inggris yang dikenal, dan menahan 289 phishing latih yang skornya belum diperiksa [Kesimpulan 8; Hasil 9-3c].
- **Email sah bertema bank dan akun bisa berpita HIGH** pada contoh fiktif E11 (hipotesis: kepekaan pada kosakata akun dan bank) [Hasil 10].
- **Kebocoran tingkat merek atau kit (hipotesis).** Merek atau templat baru bisa jauh lebih sulit: tiga bank ditahan bersamaan 0,245 [Hasil 7-4].
- **Titik lemah (hipotesis, n kecil):** phishing tanpa HTML terdeteksi 18 dari 27 dan yang berlampiran 0,750 pada test [Hasil 8-6].
- **Kosakata memuat nama orang** (mis. annie, paul), berasal dari email publik di korpus. Kosakata gabungan 18730 kata tidak diperiksa mekanis untuk nama atau data pribadi lain; kata langka yang dibuang tidak tersimpan di berkas model [Hasil 9-1; Hasil 13a].
- **Penjelasan kata bukan sebab-akibat.** Daftar kata pendorong adalah bobot statistik, dan kata penjauh dari phishing didominasi penanda sumber (hipotesis) [Hasil 9-1; Hasil 9-2].
- **Skor sama pada ambang (ties)** belum diperiksa [Hasil 7-4].

## Integritas, versi, dan cara memuat

- Berkas: `models/fold0.joblib` sampai `fold4.joblib` (total 4998468 byte), dirilis sebagai satu zip lewat GitHub Release. Nilai SHA256 tiap model ada di [docs/model_manifest.json](model_manifest.json); awalan: `27ebc383021c`, `fbdcd509788d`, `0ca8193873bf`, `5844df5baa41`, `86f85db6e163`. Zip `phishing-models-v1.zip` (rilis v1.0.0, 2678249 byte) memiliki SHA256 `24792390c0f2d86375014ac953ea5b1f98702373982a5ee09bb96d19adb58100`.
- Versi saat model dilatih: Python 3.14.3, scikit-learn 1.9.1, numpy 2.5.4, pandas 3.0.6, scipy 1.18.1 (manifest), joblib 1.6.0 (daftar paket). Model terikat versi persis ini [Hasil 13a].
- Format joblib adalah pickle: memuat berkas yang diubah dapat menjalankan kode. Hash SHA256 membuktikan integritas (berkas sama dengan yang dirilis), BUKAN keamanan (berkas yang dirilis pun harus dipercaya).
- Muat hanya lewat `src.frozen_model.muat_ensemble` (atau `src.penilai.muat_penilai` di aplikasi), yang memeriksa SHA256 sebelum `joblib.load`. Pada uji, satu byte yang diubah ditolak dengan galat "SHA256 tidak cocok" dan model tidak dimuat [Hasil 13a].
