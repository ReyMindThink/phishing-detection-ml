"""Tahap 5d-2: model teks pertama (hanya body_text), TF-IDF di DALAM tiap lipatan.
Hanya data train + 5 lipatan CV (splits.csv). Test dibuang. Hanya angka agregat."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             f1_score, roc_auc_score)
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "has_html", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
df["has_html"] = df["has_html"].astype(str) == "True"
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
ph = y == "phishing"
html = df["has_html"].to_numpy()
print("Train:", len(df), "| HTML:", int(html.sum()))

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
    print("lipatan", k, "| ukuran kosakata (dihitung hanya dari lipatan latih):",
          len(model.named_steps["tfidf"].vocabulary_))

pred = np.array(URUTAN)[oof.argmax(axis=1)]
p = oof[:, 2]


def per_lipatan(mask):
    return [average_precision_score(ph[mask & (fold == k)], p[mask & (fold == k)])
            for k in range(5)]


semua = np.ones(len(df), dtype=bool)
print("\n=== SEMUA train (acak PR-AUC phishing = %.3f) ===" % ph.mean())
pl = per_lipatan(semua)
print("macro-F1=%.3f  PR-AUC phishing=%.3f (per lipatan %.3f-%.3f)" % (
    f1_score(y, pred, average="macro"), average_precision_score(ph, p), min(pl), max(pl)))
m = y != "ham"
print("AUC phishing vs spam=%.3f | vs ham=%.3f" % (
    roc_auc_score(ph[m], p[m]), roc_auc_score(ph[y != "spam"], p[y != "spam"])))
print("\nConfusion matrix (baris = benar, kolom = tebakan):")
print(pd.DataFrame(confusion_matrix(y, pred, labels=URUTAN),
                   index=URUTAN, columns=URUTAN).to_string())

print("\n=== Di dalam email HTML saja (n=%d; acak = %.3f) ===" % (html.sum(), ph[html].mean()))
pl = per_lipatan(html)
sp_html = html & (y != "ham")
print("PR-AUC phishing=%.3f (per lipatan %.3f-%.3f) | AUC phishing vs spam=%.3f (n=%d)" % (
    average_precision_score(ph[html], p[html]), min(pl), max(pl),
    roc_auc_score(ph[sp_html], p[sp_html]), sp_html.sum()))

print("\n=== Recall phishing (tebakan terbanyak) per file Nazario ===")
for s in sorted(df.loc[ph, "subset"].unique()):
    mk = (df["subset"] == s).to_numpy()
    print("%-16s n=%4d  recall=%.3f" % (s, mk.sum(), (pred[mk] == "phishing").mean()))