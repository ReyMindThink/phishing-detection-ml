"""Tahap 7-4: tuning C (kekuatan regularisasi) LogReg teks-saja. Satu perubahan: C.
Dinilai di CV lama DAN leave-one-brand-out (purge) DAN 3 bank ditahan bersamaan.
Data train saja. Hanya angka agregat. Uji 3-bank-gabungan bersifat EKSPLORATIF."""
import warnings

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]
TARGET = 0.93
MIN_N, MAX_MEREK = 30, 20
GRID = [0.1, 0.3, 1, 3, 10, 30]
BANK3 = ["53.com", "bbt.com", "security.53.com"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "sender_domain", "body_text"])
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "group_final", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
grup = df["group_final"].to_numpy()
dom = df["sender_domain"].to_numpy()
ph = y == "phishing"
KONV = [0]


def proba(C, tr, te):
    m = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                  min_df=3, max_features=20000, sublinear_tf=True)),
        ("clf", LogisticRegression(C=C, max_iter=1000, random_state=42)),
    ])
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        m.fit(df.loc[tr, "body_text"], y[tr])
    KONV[0] += sum(issubclass(x.category, ConvergenceWarning) for x in w)
    urut = [list(m.classes_).index(c) for c in URUTAN]
    return m.predict_proba(df.loc[te, "body_text"])[:, urut]


def purge(te):
    return ph & np.isin(grup, np.unique(grup[te]))


cnt = pd.Series(dom[ph & (dom != "")]).value_counts()
merek = [d for d, n in cnt.items() if n >= MIN_N][:MAX_MEREK]
te3 = ph & np.isin(dom, BANK3)
assert len(merek) == 16 and te3.sum() == 212, (len(merek), te3.sum())  # CTRL

print("C | PR-AUC | macroF1(argmax) | ambang | precision (tp/n) FP ham/spam | "
      "LOBO16 recall (hit/n) | 53.com | 3 bank gabungan | peringatan konvergensi")
baris = []
for C in GRID:
    KONV[0] = 0
    oof = np.zeros((len(df), 3))
    for k in range(5):
        va = fold == k
        oof[va] = proba(C, ~va, va)
    p = oof[:, 2]
    t = np.sort(p[ph])[::-1][int(np.ceil(TARGET * ph.sum())) - 1]
    lain = np.where(oof[:, 0] >= oof[:, 1], "ham", "spam")
    pred = np.where(p >= t, "phishing", lain)
    tp, n_pred = int(((pred == "phishing") & ph).sum()), int((pred == "phishing").sum())
    fp_h = int(((pred == "phishing") & (y == "ham")).sum())
    fp_s = int(((pred == "phishing") & (y == "spam")).sum())
    hit = n = 0
    r53 = 0.0
    for d in merek:
        te = ph & (dom == d)
        h = int((proba(C, ~purge(te), te)[:, 2] >= t).sum())
        hit, n = hit + h, n + int(te.sum())
        if d == "53.com":
            r53 = h / te.sum()
    r3 = (proba(C, ~purge(te3), te3)[:, 2] >= t).mean()
    if C == 1:                                  # KONTROL: reproduksi 7-1 / 7-2 / 7-3
        assert abs(t - 0.5040) < 5e-5 and (tp, n_pred) == (2513, 2549), (t, tp, n_pred)  # CTRL
        assert (hit, n) == (1586, 1689), (hit, n)  # CTRL
        print("KONTROL OK (C=1): ambang 0,5040; precision 2513/2549; LOBO16 1586/1689")
    pa = average_precision_score(ph, p)
    print("%-4g | %.3f | %.3f | %.4f | %.3f (%d/%d) %d/%d | %.3f (%d/%d) | %.3f | %.3f | %d" % (
        C, pa, f1_score(y, np.array(URUTAN)[oof.argmax(axis=1)], average="macro"), t,
        tp / n_pred, tp, n_pred, fp_h, fp_s, hit / n, hit, n, r53, r3, KONV[0]))
    baris.append((C, tp / n_pred, hit / n, KONV[0]))

dasar = [b for b in baris if b[0] == 1][0]
kand = [b for b in baris if b[0] != 1 and b[1] - dasar[1] >= 0.005
        and b[2] - dasar[2] >= -0.01 and b[3] == 0]
print("\nAturan terkunci: precision naik >= 0,005 DAN LOBO16 tidak turun > 0,01 "
      "DAN tanpa peringatan konvergensi.")
print("Hasil:", ("C terpilih = %g" % max(kand, key=lambda b: b[1])[0]) if kand
      else "tidak ada kandidat; C=1 dipertahankan")