"""Tahap 8-3-2: evaluasi eksternal MeAJOR pada model beku (HANYA persen ditandai).

Bukan recall dan bukan false positive ham modern: label 1 = spam TREC, teks teranonimkan.
Test set DIBUANG di awal; hanya angka agregat. Aturan dan prediksi dikunci di docs/experiment_design.md.
Jalankan: python -m src.eval_meajor
"""
import os
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix

from src.frozen_model import URUTAN, muat_ensemble, proba_ensemble, putusan

PATH = "data/raw/meajor_cleaned_preprocessed.parquet.gzip"
TOKEN_RE = re.compile(r"\[[A-Z][A-Z0-9_]{1,30}\]")
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
tanda = oof[:, 2] >= t
fp_ham, fp_spam = int((tanda & (y == "ham")).sum()), int((tanda & (y == "spam")).sum())
if KONTROL:
    cm = confusion_matrix(y, np.array(URUTAN)[oof.argmax(axis=1)], labels=URUTAN)
    assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
    assert (int((tanda & (y == "phishing")).sum()), int(tanda.sum())) == (2513, 2549)
    print("KONTROL OK: OOF 3245/1317/2584 dan 2513/2549")
print("Pembanding OOF pada ambang: ham ditandai phishing %d/%d (%.2f%%), spam %d/%d (%.2f%%)" % (
    fp_ham, (y == "ham").sum(), 100 * fp_ham / (y == "ham").sum(),
    fp_spam, (y == "spam").sum(), 100 * fp_spam / (y == "spam").sum()))

mj = pd.read_parquet(PATH, columns=["body", "label", "source"]).dropna(subset=["body", "label"])
mj = mj.reset_index(drop=True)
mj["label"] = mj["label"].astype(int)
if KONTROL:
    assert len(mj) == 108683 and mj["label"].value_counts().to_dict() == {0: 60649, 1: 48034}
teks = mj["body"].str.replace(TOKEN_RE, " ", regex=True)
lab = mj["label"].to_numpy()
src = mj["source"].to_numpy()

vec = TfidfVectorizer(min_df=2, sublinear_tf=True, max_features=50000)
Xtr = vec.fit_transform(tr["body_text"]).T.tocsc()
Xm = vec.transform(teks)
maks = np.zeros(len(mj))
tetangga = np.zeros(len(mj), dtype=int)
for a in range(0, len(mj), 2000):
    S = (Xm[a:a + 2000] @ Xtr).toarray()
    tetangga[a:a + 2000] = S.argmax(axis=1)
    maks[a:a + 2000] = S.max(axis=1)
dup = maks >= BATAS_DUP
utama = ~dup
print("\nDuplikat terhadap train (cosine maks; n label 0 = %d, label 1 = %d)" % ((lab == 0).sum(), (lab == 1).sum()))
for b in (0.9, 0.8, 0.7):
    print("  >= %.1f: label 0 %d | label 1 %d" % (b, ((maks >= b) & (lab == 0)).sum(), ((maks >= b) & (lab == 1)).sum()))
if dup.any():
    print("Kelas train terdekat, baris >= %.1f (label MeAJOR x kelas train):" % BATAS_DUP)
    print(pd.crosstab(lab[dup], y[tetangga[dup]]).to_string())

n_kata, n_kata_tr = teks.str.count(KATA_RE), tr["body_text"].str.count(KATA_RE)
print("\nJumlah kata (>= 3 huruf), median: MeAJOR label 0 %.0f | label 1 %.0f | train ham %.0f | spam %.0f | phishing %.0f" % (
    n_kata[lab == 0].median(), n_kata[lab == 1].median(), n_kata_tr[y == "ham"].median(),
    n_kata_tr[y == "spam"].median(), n_kata_tr[y == "phishing"].median()))
print("Baris tanpa satu pun kata >= 3 huruf: label 0 %d | label 1 %d" % (
    ((n_kata == 0) & (lab == 0)).sum(), ((n_kata == 0) & (lab == 1)).sum()))

proba = np.vstack([proba_ensemble(models, teks.iloc[a:a + 20000]) for a in range(0, len(mj), 20000)])
pred = putusan(proba, t)


def baris(nama, m):
    n = int(m.sum())
    if n == 0:
        print("%-26s n=0" % nama)
        return
    p = [(pred[m] == c).mean() * 100 for c in URUTAN]
    print("%-26s n=%-6d%s ham %5.2f%% | spam %5.2f%% | phishing %5.2f%% | median P(phishing) %.3f" % (
        nama, n, "*" if n < 30 else " ", p[0], p[1], p[2], np.median(proba[m, 2])))


print("\nPutusan model beku (ambang eksak %r)" % t)
for nama, pop in (("POPULASI UTAMA (cos < 0,9)", utama), ("semua baris (diagnostik)", np.ones(len(mj), bool))):
    print(nama)
    for l in (0, 1):
        baris("  label %d" % l, pop & (lab == l))
print("Per sumber, populasi utama:")
for s in sorted(set(src)):
    for l in (0, 1):
        baris("  %s label %d" % (s, l), utama & (lab == l) & (src == s))

r0 = (pred[utama & (lab == 0)] == "phishing").mean() * 100
print("\nAturan baca terkunci: label 0 ditandai phishing %.2f%% -> %s" % (
    r0, "<= 1,0%: tidak ada tanda FP massal (format anonim)" if r0 <= 1.0
    else "> 1,0%: kerapuhan ATAU artefak format, tidak terpisahkan"))