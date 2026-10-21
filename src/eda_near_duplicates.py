"""Near-duplicate via TF-IDF cosine. Hanya angka agregat.

Sebelum itu: buang email kosong dan duplikat exact.
Untuk tiap email dihitung kemiripan tertinggi ke email LAIN dengan label sama
dan dengan label berbeda.
"""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

df = pd.read_csv("data/processed/emails_all.csv", keep_default_na=False)
df = df[~((df["subject"] == "") & (df["body_text"] == ""))]
df = df.drop_duplicates("content_hash").reset_index(drop=True)
print("Setelah buang kosong + duplikat exact:", len(df))
print(df["label"].value_counts().to_string())

teks = (df["subject"] + " " + df["body_text"]).tolist()
X = TfidfVectorizer(min_df=2, sublinear_tf=True, max_features=50000).fit_transform(teks)
labels = df["label"].to_numpy()
n = len(df)

max_sama = np.zeros(n)
max_beda = np.zeros(n)
for mulai in range(0, n, 1000):
    S = (X[mulai:mulai + 1000] @ X.T).toarray()
    for k in range(S.shape[0]):
        S[k, mulai + k] = 0.0
    sama = labels[mulai:mulai + 1000, None] == labels[None, :]
    max_sama[mulai:mulai + 1000] = np.where(sama, S, 0).max(axis=1)
    max_beda[mulai:mulai + 1000] = np.where(~sama, S, 0).max(axis=1)

print("\n=== % email yang punya near-duplicate (kemiripan >= ambang) ===")
for label in ["ham", "spam", "phishing"]:
    m = labels == label
    baris = [f"{label:9}"]
    for t in (0.8, 0.9, 0.95):
        baris.append(f"sama-label>={t}: {(max_sama[m] >= t).mean()*100:5.1f}%")
    for t in (0.8, 0.9):
        baris.append(f"label-lain>={t}: {(max_beda[m] >= t).mean()*100:5.1f}%")
    print(" | ".join(baris))