"""Tahap 8-4-2: uji phishing modern (Nazario 2015-2025) pada model beku: HANYA recall.

Tidak ada ham modern, jadi precision TIDAK bisa diukur. Test set DIBUANG di awal; hanya agregat.
Aturan, varian populasi, dan prediksi dikunci di docs/experiment_design.md sebelum skrip ini jalan.
Jalankan: python -m src.eval_nazario_modern
"""
import os

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix

from src.frozen_model import URUTAN, muat_ensemble, proba_ensemble, putusan

PATH = "data/interim/nazario_modern/nazario_modern_clean.csv"
KATA_RE = r"\b[a-zA-Z]{3,}\b"
KONTROL = os.environ.get("UJI_ALUR_SINTETIS") != "1"    # "1" HANYA untuk menguji alur pada data sintetis
BATAS_DUP = 0.9

tr = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
tr = tr.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert tr["split"].notna().all(), "ada email tanpa indeks split"
tr = tr[tr["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
if KONTROL:
    assert len(tr) == 7438, len(tr)
y = tr["label"].to_numpy()
fold = tr["fold"].to_numpy()

models, manifest = muat_ensemble()
t = manifest["ambang"]
oof = np.zeros((len(tr), 3))
for k, m in enumerate(models):
    va = fold == k
    urut = [list(m.classes_).index(c) for c in URUTAN]
    oof[va] = m.predict_proba(tr["body_text"][va])[:, urut]
if KONTROL:
    cm = confusion_matrix(y, np.array(URUTAN)[oof.argmax(axis=1)], labels=URUTAN)
    assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
    tanda = oof[:, 2] >= t
    assert (int((tanda & (y == "phishing")).sum()), int(tanda.sum())) == (2513, 2549)
    print("KONTROL OK: OOF 3245/1317/2584 dan 2513/2549")

mo = pd.read_csv(PATH, keep_default_na=False, usecols=["source_file", "content_hash", "body_text"])
n_baris = len(mo)
if KONTROL:
    assert n_baris == 3466 and int((mo["body_text"].str.strip() == "").sum()) == 84
mo = mo.drop_duplicates("content_hash").reset_index(drop=True)
kosong = (mo["body_text"].str.strip() == "").to_numpy()
print("Baris %d | unik (hash) %d | duplikat exact dibuang %d (%.1f%%) | body kosong di antara unik %d" % (
    n_baris, len(mo), n_baris - len(mo), 100 * (n_baris - len(mo)) / n_baris, kosong.sum()))

vec = TfidfVectorizer(min_df=2, sublinear_tf=True, max_features=50000)
Xtr = vec.fit_transform(tr["body_text"])
Xm = vec.transform(mo["body_text"])
S = (Xm @ Xtr.T.tocsc()).toarray()
maks, tetangga = S.max(axis=1), S.argmax(axis=1)
dup = maks >= BATAS_DUP
print("\nMirip train (cosine maks), di antara unik tidak kosong (n=%d): >= 0.9: %d | >= 0.8: %d | >= 0.7: %d" % (
    (~kosong).sum(), (dup & ~kosong).sum(), ((maks >= 0.8) & ~kosong).sum(), ((maks >= 0.7) & ~kosong).sum()))
print("Kelas train terdekat untuk yang >= 0.9:", pd.Series(y[tetangga[dup & ~kosong]]).value_counts().to_dict())
n_grup, grup = connected_components(((Xm @ Xm.T) >= BATAS_DUP), directed=False)

n_kata, n_kata_tr = mo["body_text"].str.count(KATA_RE), tr["body_text"].str.count(KATA_RE)
proba = proba_ensemble(models, mo["body_text"])
pred = putusan(proba, t)
flag = pred == "phishing"


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


varian = {"A primer: unik, tidak kosong, cos < 0,9": ~kosong & ~dup,
          "B: unik, tidak kosong": ~kosong,
          "C: semua unik (kosong ikut)": np.ones(len(mo), bool)}
rec = {}
print("\nRecall phishing pada ambang eksak %r (HANYA recall; precision tidak terukur)" % t)
for nama, m in varian.items():
    k, n = int(flag[m].sum()), int(m.sum())
    lo, hi = wilson(k, n)
    rec[nama] = k / n
    print("%-42s recall %.4f (%d/%d)  Wilson 95%% [%.3f, %.3f]" % (nama, k / n, k, n, lo, hi))
r = min(rec.values())
print("Aturan baca terkunci (varian terendah %.4f): %s" % (
    r, ">= 0,90: tahan terhadap phishing modern dari pengumpul yang sama" if r >= 0.90
    else "0,70-0,90: sebagian" if r >= 0.70
    else "< 0,70: klaim README dibatasi pada phishing klasik 2002-2007"))

a = varian["A primer: unik, tidak kosong, cos < 0,9"]
print("\nVarian A per file (n; * bila n < 30):")
for f in sorted(set(mo["source_file"])):
    m = a & (mo["source_file"].to_numpy() == f)
    if m.sum():
        print("  %-14s n=%-4d%s recall %.3f" % (f, m.sum(), "*" if m.sum() < 30 else " ", flag[m].mean()))
pg = pd.Series(flag[a]).groupby(grup[a]).mean()
ukuran = pd.Series(grup[a]).value_counts()
print("Varian A per grup (cosine >= 0,9 di dalam set modern): %d grup | recall rata-rata per grup %.4f | grup terbesar %d email (%.1f%% dari A)" % (
    len(pg), pg.mean(), ukuran.iloc[0], 100 * ukuran.iloc[0] / a.sum()))
print("Putusan varian A (ham/spam/phishing): %s" % " / ".join("%.1f%%" % (100 * (pred[a] == c).mean()) for c in URUTAN))
print("Median P(phishing) varian A: %.3f | persentil 10: %.3f" % (np.median(proba[a, 2]), np.quantile(proba[a, 2], 0.1)))
print("Deskriptif (BUKAN penyetelan ambang) recall varian A pada ambang lain: " + " | ".join(
    "%.3f: %.3f" % (th, (proba[a, 2] >= th).mean()) for th in (0.2, 0.3, 0.4, t, 0.6, 0.7)))
print("Median jumlah kata (>= 3 huruf): modern varian A %.0f | train phishing %.0f" % (
    n_kata[a].median(), n_kata_tr[y == "phishing"].median()))