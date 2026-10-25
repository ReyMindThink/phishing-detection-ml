"""Tahap 5d-5: phishing terlewat dihitung per email DAN per grup (group_final).
Hanya train + 5 lipatan. Hanya angka agregat (id grup = angka, tanpa isi email)."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "body_text"])
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "split", "fold", "group_final"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()

pred = np.empty(len(df), dtype=object)
for k in range(5):
    va = fold == k
    model = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3,
                                  max_features=20000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(df.loc[~va, "body_text"], y[~va])
    kelas = list(model.classes_)
    pred[va] = np.array(kelas)[model.predict_proba(df.loc[va, "body_text"]).argmax(axis=1)]

ph = y == "phishing"
assert (ph & (pred != "phishing")).sum() == 118, "hasil tidak sama dgn cv_text.py"
print("OK: phishing terlewat = 118 (sama dengan cv_text.py)")

campur = df.groupby("group_final")["label"].nunique()
grup_ph = df.loc[ph, "group_final"].unique()
print("Grup yang berisi phishing: %d | di antaranya campur kelas: %d" % (
    len(grup_ph), int((campur.loc[grup_ph] > 1).sum())))

d = pd.DataFrame({"g": df.loc[ph, "group_final"].to_numpy(),
                  "subset": df.loc[ph, "subset"].to_numpy(),
                  "ok": (pred[ph] == "phishing")})
agg = d.groupby("g").agg(n=("ok", "size"), benar=("ok", "sum"), subset=("subset", "first"))
agg["salah"] = agg["n"] - agg["benar"]
agg["rec"] = agg["benar"] / agg["n"]

print("\n=== Recall phishing: per email vs per grup ===")
print("Per email : %.3f (%d email)" % (d["ok"].mean(), len(d)))
print("Per grup  : %.3f (rata-rata recall tiap grup, bobot sama; %d grup)" % (agg["rec"].mean(), len(agg)))
print("Grup terdeteksi semua: %d | sebagian: %d | terlewat semua: %d" % (
    (agg["rec"] == 1).sum(), ((agg["rec"] > 0) & (agg["rec"] < 1)).sum(), (agg["rec"] == 0).sum()))
print("Grup dengan >= 1 kesalahan: %d (dari 118 email terlewat)" % (agg["salah"] > 0).sum())

print("\n=== Recall menurut ukuran grup ===")
agg["ukuran"] = pd.cut(agg["n"], [0, 1, 5, 20, 10**6], labels=["1", "2-5", "6-20", ">20"])
print("%-6s %7s %7s %12s %12s" % ("ukuran", "n_grup", "n_email", "recall_email", "recall_grup"))
for u, g in agg.groupby("ukuran", observed=True):
    print("%-6s %7d %7d %12.3f %12.3f" % (u, len(g), g["n"].sum(), g["benar"].sum() / g["n"].sum(),
                                          g["rec"].mean()))

print("\n=== Konsentrasi kesalahan ===")
urut = agg.sort_values("salah", ascending=False)
total = int(agg["salah"].sum())
for t in (1, 3, 5, 10):
    print("%2d grup teratas menanggung %3d dari %d kesalahan (%.1f%%)" % (
        t, urut["salah"].head(t).sum(), total, urut["salah"].head(t).sum() / total * 100))
print("\n10 grup dengan kesalahan terbanyak:")
print(urut[["subset", "n", "salah"]].head(10).to_string())