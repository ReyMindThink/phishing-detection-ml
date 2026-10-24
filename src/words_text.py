"""Tahap 5d-3: kata mana yang dipakai model teks, dan mengapa phishing0 lemah?
Hanya data train + 5 lipatan (splits.csv). Test dibuang. Hanya kata dan angka agregat."""
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]
TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
TOP, MINIMAL = 30, 4          # 30 kata teratas per kelas; stabil bila muncul di >= 4 dari 5 lipatan

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

hitung = {c: Counter() for c in URUTAN}
pred = np.empty(len(df), dtype=object)
for k in range(5):
    va = fold == k
    model = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3,
                                  max_features=20000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(df.loc[~va, "body_text"], y[~va])
    kata = np.array(model.named_steps["tfidf"].get_feature_names_out())
    coef = model.named_steps["clf"].coef_
    kelas = list(model.classes_)
    for c in URUTAN:
        teratas = np.argsort(coef[kelas.index(c)])[::-1][:TOP]
        hitung[c].update(kata[teratas])
    pred[va] = np.array(kelas)[model.predict_proba(df.loc[va, "body_text"]).argmax(axis=1)]

stabil = {c: sorted([w for w, n in hitung[c].items() if n >= MINIMAL],
                    key=lambda w: (-hitung[c][w], w)) for c in URUTAN}
semua = sorted(set(w for ws in stabil.values() for w in ws))
cv = CountVectorizer(token_pattern=TOKEN, lowercase=True, binary=True, vocabulary=semua)
X = cv.transform(df["body_text"])
persen = {k: np.asarray(X[y == k].mean(axis=0)).ravel() * 100 for k in URUTAN}

print("Deskriptif pada train (persen email per kelas yang memuat kata); BUKAN input model.")
for c in URUTAN:
    print(f"\n=== Kelas {c}: {len(stabil[c])} dari {TOP} kata stabil (>= {MINIMAL}/5 lipatan) ===")
    print(f"{'kata':14} {'lipatan':>7} {'%ham':>6} {'%spam':>6} {'%phish':>7}")
    for w in stabil[c]:
        j = cv.vocabulary_[w]
        print(f"{w:14} {hitung[c][w]:>7} {persen['ham'][j]:6.1f} {persen['spam'][j]:6.1f} "
              f"{persen['phishing'][j]:7.1f}")

# --- Mengapa phishing0 lemah? ---
p0 = (df["subset"] == "phishing0.mbox").to_numpy()
salah = p0 & (pred != "phishing")
benar = p0 & (pred == "phishing")
print(f"\n=== phishing0 (train): n={p0.sum()} | terdeteksi={benar.sum()} | terlewat={salah.sum()} ===")
print("Terlewat diprediksi sebagai:", pd.Series(pred[salah]).value_counts().to_dict())
for nama, m in [("terlewat", salah), ("terdeteksi", benar)]:
    teks = df.loc[m, "body_text"].str.len()
    print(f"{nama:10} median panjang teks={teks.median():.0f} karakter | "
          f"%HTML={df.loc[m, 'has_html'].mean() * 100:.1f}")

cv0 = CountVectorizer(token_pattern=TOKEN, lowercase=True, binary=True, min_df=5)
cv0.fit(df.loc[p0, "body_text"])
kata0 = np.array(cv0.get_feature_names_out())
a = np.asarray(cv0.transform(df.loc[salah, "body_text"]).mean(axis=0)).ravel() * 100
b = np.asarray(cv0.transform(df.loc[benar, "body_text"]).mean(axis=0)).ravel() * 100
print(f"\n20 kata dengan selisih terbesar (lebih sering di terlewat n={salah.sum()} "
      f"daripada di terdeteksi n={benar.sum()}); n kecil, hanya petunjuk:")
print(f"{'kata':14} {'%terlewat':>10} {'%terdeteksi':>12}")
for j in np.argsort(a - b)[::-1][:20]:
    print(f"{kata0[j]:14} {a[j]:10.1f} {b[j]:12.1f}")