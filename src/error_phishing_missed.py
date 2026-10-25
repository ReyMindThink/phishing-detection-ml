"""Tahap 5d-4: error analysis phishing yang terlewat model teks (label noise atau
kegagalan model?). Hanya train + 5 lipatan. Hanya angka agregat, tanpa isi email."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]
TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "group_id", "has_html",
                          "has_list_header", "n_headers", "body_text"])
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "split", "fold", "group_final"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
for c in ["has_html", "has_list_header"]:
    df[c] = df[c].astype(str) == "True"
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
miss = ph & (pred != "phishing")
p0 = (df["subset"] == "phishing0.mbox").to_numpy()
assert (p0 & ~miss & ph).sum() == 213 and (p0 & miss).sum() == 35, "hasil tidak sama dgn cv_text.py"
print("OK: hasil sama dengan cv_text.py (phishing0 terdeteksi 213, terlewat 35)")

print("\nPhishing terlewat total: %d dari %d (recall %.3f)" % (miss.sum(), ph.sum(), 1 - miss.sum() / ph.sum()))
print("\n=== Per subset phishing ===")
for s in sorted(df.loc[ph, "subset"].unique()):
    m = (df["subset"] == s).to_numpy() & ph
    print("%-16s n=%4d terlewat=%3d recall=%.3f" % (s, m.sum(), (m & miss).sum(),
                                                    1 - (m & miss).sum() / m.sum()))
print("\n=== Phishing terlewat per lipatan ===")
print({k: int((miss & (fold == k)).sum()) for k in range(5)})

cv = CountVectorizer(token_pattern=TOKEN, lowercase=True, binary=True,
                     vocabulary=["gnupg", "pgp"])
X = cv.transform(df["body_text"]).toarray().astype(bool)
ada_gnupg, ada_pgp = X[:, 0], X[:, 1]

print("\n=== Email train yang memuat 'gnupg': per kelas dan subset ===")
print(pd.crosstab(df.loc[ada_gnupg, "label"], df.loc[ada_gnupg, "subset"]).to_string())
print("\nPhishing terlewat per subset, dan yang memuat 'gnupg':")
for s in sorted(df.loc[miss, "subset"].unique()):
    m = (df["subset"] == s).to_numpy() & miss
    print("%-16s terlewat=%3d memuat gnupg=%3d" % (s, m.sum(), (m & ada_gnupg).sum()))

kl = p0 & miss & ada_gnupg
print("\n=== Kluster: phishing0 terlewat yang memuat 'gnupg' (n=%d; juga memuat 'pgp': %d) ==="
      % (kl.sum(), (kl & ada_pgp).sum()))
print("Terlewat diprediksi sebagai:", pd.Series(pred[kl]).value_counts().to_dict())
print("group_id berbeda: %d | group_final berbeda: %d | lipatan berbeda: %d" % (
    df.loc[kl, "group_id"].nunique(), df.loc[kl, "group_final"].nunique(),
    df.loc[kl, "fold"].nunique()))
g = df.loc[kl, "group_id"].value_counts()
ukuran = df.groupby("group_id").size()
print("Anggota kluster per group_id:", g.values.tolist())
print("Ukuran penuh grup-grup itu di train:", [int(ukuran[i]) for i in g.index])
print("Label seluruh anggota grup-grup itu:",
      df[df["group_id"].isin(g.index)]["label"].value_counts().to_dict())
print("Kluster: median panjang teks=%.0f | %%HTML=%.1f | %%header milis=%.1f | median n_headers=%.0f" % (
    df.loc[kl, "body_text"].str.len().median(), df.loc[kl, "has_html"].mean() * 100,
    df.loc[kl, "has_list_header"].mean() * 100, df.loc[kl, "n_headers"].median()))
rest = p0 & miss & ~ada_gnupg
print("Terlewat phishing0 di luar kluster (n=%d): diprediksi %s" % (
    rest.sum(), pd.Series(pred[rest]).value_counts().to_dict()))