"""Tahap 7-1: baseline teks-saja (TF-IDF + LogReg), OOF 5 lipatan, ambang dari OOF.
Hanya data train. Test dibuang di awal. Hanya angka agregat."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "body_text"])
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "group_final", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
grup = df["group_final"].to_numpy()
ph = y == "phishing"

oof = np.zeros((len(df), 3))
for k in range(5):
    va = fold == k
    model = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                  min_df=3, max_features=20000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(df.loc[~va, "body_text"], y[~va])
    urut = [list(model.classes_).index(c) for c in URUTAN]
    oof[va] = model.predict_proba(df.loc[va, "body_text"])[:, urut]

# KONTROL: harus mereproduksi angka Tahap 5d-2 sebelum hasil baru dipercaya
cm = confusion_matrix(y, np.array(URUTAN)[oof.argmax(axis=1)], labels=URUTAN)
assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
assert ph.sum() == 2702 and len(np.unique(grup[ph])) == 1629
print("KONTROL OK: diagonal 3245/1317/2584, 2702 phishing dalam 1629 grup")

p = oof[:, 2]                                   # P(phishing)
lain = np.where(oof[:, 0] >= oof[:, 1], "ham", "spam")   # tebakan bila bukan phishing


def ambang(target):
    """Ambang TERTINGGI yang masih memberi recall phishing >= target (pada OOF)."""
    s = np.sort(p[ph])[::-1]
    return s[int(np.ceil(target * ph.sum())) - 1]


print("\nTarget recall | ambang | recall email | recall grup | precision | "
      "FP dari ham/spam | macro-F1 | recall per lipatan (min-maks)")
for target in (0.90, 0.93, 0.95):
    t = ambang(target)
    pred = np.where(p >= t, "phishing", lain)
    tp = int(((pred == "phishing") & ph).sum())
    n_pred = int((pred == "phishing").sum())
    fp_ham = int(((pred == "phishing") & (y == "ham")).sum())
    fp_spam = int(((pred == "phishing") & (y == "spam")).sum())
    hit = pd.Series(pred[ph] == "phishing").groupby(grup[ph]).mean()
    per_lip = [(pred[ph & (fold == k)] == "phishing").mean() for k in range(5)]
    print("%.2f | %.4f | %.3f | %.3f | %.3f (%d/%d) | %d/%d | %.3f | %.3f-%.3f" % (
        target, t, tp / ph.sum(), hit.mean(), tp / n_pred, tp, n_pred,
        fp_ham, fp_spam, f1_score(y, pred, average="macro"), min(per_lip), max(per_lip)))