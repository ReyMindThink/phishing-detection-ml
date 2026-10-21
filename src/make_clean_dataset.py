"""Bersihkan data dan beri group_id untuk near-duplicate (kemiripan >= AMBANG).

Hanya mencetak angka agregat.
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer

AMBANG = 0.9

df = pd.read_csv("data/processed/emails_all.csv", keep_default_na=False)
df = df[~((df["subject"] == "") & (df["body_text"] == ""))]
df = df.drop_duplicates("content_hash").reset_index(drop=True)
n = len(df)

teks = (df["subject"] + " " + df["body_text"]).tolist()
X = TfidfVectorizer(min_df=2, sublinear_tf=True, max_features=50000).fit_transform(teks)

baris, kolom = [], []
for mulai in range(0, n, 1000):
    S = (X[mulai:mulai + 1000] @ X.T).toarray()
    r, c = np.nonzero(S >= AMBANG)
    baris.append(r + mulai)
    kolom.append(c)
baris, kolom = np.concatenate(baris), np.concatenate(kolom)
G = coo_matrix((np.ones(len(baris)), (baris, kolom)), shape=(n, n))
_, df["group_id"] = connected_components(G, directed=False)

df.to_csv("data/processed/emails_clean.csv", index=False)

print("Total email:", n, "| total grup:", df["group_id"].nunique())
print("\nPer label:")
for label, g in df.groupby("label"):
    ukuran = g.groupby("group_id").size()
    persen_berkelompok = ukuran[ukuran > 1].sum() / len(g) * 100
    print(f"{label:9} email={len(g):5} grup={len(ukuran):5} "
          f"grup_terbesar={ukuran.max():4} email_di_grup>1={persen_berkelompok:5.1f}%")
campur = df.groupby("group_id")["label"].nunique()
print("\nGrup berisi lebih dari satu label:", int((campur > 1).sum()))