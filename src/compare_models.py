"""Tahap 7-2: bandingkan klasifier dengan fitur TF-IDF yang SAMA (satu perubahan: klasifier).
Hanya data train, 5 lipatan splits.csv, test dibuang. Hanya angka agregat."""
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]
TARGET = 0.93        # keputusan 7-1 (opsi B)

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
ph = y == "phishing"

MODEL = {
    "LogReg": lambda: LogisticRegression(max_iter=1000, random_state=42),
    "RandomForest": lambda: RandomForestClassifier(
        n_estimators=300, random_state=42, n_jobs=-1),
}


def oof_untuk(buat):
    oof = np.zeros((len(df), 3))
    for k in range(5):
        va = fold == k
        m = Pipeline([
            ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                      min_df=3, max_features=20000, sublinear_tf=True)),
            ("clf", buat()),
        ])
        m.fit(df.loc[~va, "body_text"], y[~va])
        urut = [list(m.classes_).index(c) for c in URUTAN]
        oof[va] = m.predict_proba(df.loc[va, "body_text"])[:, urut]
    return oof


def laporan(nama, oof, detik):
    p = oof[:, 2]
    pred0 = np.array(URUTAN)[oof.argmax(axis=1)]
    pl = [average_precision_score(ph[fold == k], p[fold == k]) for k in range(5)]
    t = np.sort(p[ph])[::-1][int(np.ceil(TARGET * ph.sum())) - 1]
    lain = np.where(oof[:, 0] >= oof[:, 1], "ham", "spam")
    pred = np.where(p >= t, "phishing", lain)
    tp = int(((pred == "phishing") & ph).sum())
    n_pred = int((pred == "phishing").sum())
    fp_h = int(((pred == "phishing") & (y == "ham")).sum())
    fp_s = int(((pred == "phishing") & (y == "spam")).sum())
    rl = [(pred[ph & (fold == k)] == "phishing").mean() for k in range(5)]
    print("%-12s PR-AUC=%.3f (lipatan %.3f-%.3f) macroF1(argmax)=%.3f | pada recall %.2f: "
          "ambang=%.4f precision=%.3f (%d/%d) FP ham/spam=%d/%d recall lipatan %.3f-%.3f | %.0f dtk"
          % (nama, average_precision_score(ph, p), min(pl), max(pl),
             f1_score(y, pred0, average="macro"), TARGET, t, tp / n_pred, tp, n_pred,
             fp_h, fp_s, min(rl), max(rl), detik))
    return pl, pred0


hasil = {}
for nama, buat in MODEL.items():
    mulai = time.time()
    oof = oof_untuk(buat)
    hasil[nama] = laporan(nama, oof, time.time() - mulai)
    if nama == "LogReg":                        # KONTROL: reproduksi angka 5d-2 / 7-1
        cm = confusion_matrix(y, hasil[nama][1], labels=URUTAN)
        assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
        print("KONTROL OK: diagonal 3245/1317/2584")

dasar = np.array(hasil["LogReg"][0])
for nama in MODEL:
    if nama == "LogReg":
        continue
    d = np.array(hasil[nama][0]) - dasar
    print("\n%s - LogReg, selisih PR-AUC per lipatan: %s | rata-rata %+.4f | membaik di %d/5"
          % (nama, " ".join("%+.4f" % x for x in d), d.mean(), int((d > 0).sum())))
    print("Aturan terkunci (selisih >= 0,005 DAN membaik di >= 4/5): %s"
          % ("TERPENUHI" if d.mean() >= 0.005 and (d > 0).sum() >= 4 else "tidak terpenuhi"))