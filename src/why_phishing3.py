"""Tahap 6-5: mengapa model teks LOFO salah menebak phishing3 sebagai ham?
Hanya TRAIN (splits.csv). Test dibuang. Hanya angka agregat, id grup, domain, dan kata."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
F = "phishing3.mbox"

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "has_html", "sender_domain", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "group_final"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
df["has_html"] = df["has_html"].astype(str) == "True"
y = df["label"].to_numpy()
sub = df["subset"].to_numpy()
tr = np.where(sub != F)[0]
te = np.where(sub == F)[0]

model = Pipeline([("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3,
                                            max_features=20000, sublinear_tf=True)),
                  ("clf", LogisticRegression(max_iter=1000, random_state=42))])
model.fit(df["body_text"].iloc[tr], y[tr])
P = model.predict_proba(df["body_text"].iloc[te])
kelas = list(model.classes_)
pred = np.array(kelas)[P.argmax(axis=1)]
n_ham, n_spam = int((pred == "ham").sum()), int((pred == "spam").sum())
assert (n_ham, n_spam) == (249, 10), (n_ham, n_spam)
print("KONTROL OK: LOFO phishing3 -> ke ham %d, ke spam %d (sama dengan 6-4)" % (n_ham, n_spam))

d = df.iloc[te].reset_index(drop=True)
ke_ham = pred == "ham"
ok = pred == "phishing"
p_ham = P[:, kelas.index("ham")]

print("\n=== A. Konsentrasi kesalahan ke ham per group_final ===")
g = d.loc[ke_ham, "group_final"].value_counts()
total = int(ke_ham.sum())
ukuran = d.groupby("group_final").size()
print("Grup berbeda di %d kesalahan: %d" % (total, len(g)))
for t in (1, 3, 5, 10):
    print("  %2d grup teratas = %3d kesalahan (%.1f%%)" % (t, g.head(t).sum(), g.head(t).sum() / total * 100))
print("  5 grup teratas (id grup: salah/ukuran grup di phishing3):",
      ", ".join("%d: %d/%d" % (i, n, ukuran[i]) for i, n in g.head(5).items()))

print("\n=== B. Domain pengirim pada kesalahan (deskriptif, bukan fitur) ===")
dom = d.loc[ke_ham, "sender_domain"].replace("", "(kosong)").value_counts()
print("Domain berbeda: %d" % len(dom))
for nm, n in dom.head(8).items():
    print("  %-28s %4d (%.1f%%)" % (nm, n, n / total * 100))

print("\n=== C. Kesalahan ke ham vs terdeteksi (phishing3) ===")
for nama, m in [("ke ham", ke_ham), ("terdeteksi", ok)]:
    print("%-10s n=%4d | median panjang teks=%5.0f | %%HTML=%.1f" % (
        nama, m.sum(), d.loc[m, "body_text"].str.len().median(), d.loc[m, "has_html"].mean() * 100))
print("Keyakinan model pada kesalahan ke ham: median P(ham)=%.2f | %%dengan P(ham)>=0,9: %.1f" % (
    np.median(p_ham[ke_ham]), (p_ham[ke_ham] >= 0.9).mean() * 100))

print("\n=== D. 25 kata lebih sering di kesalahan daripada di phishing file lain (n kecil: petunjuk) ===")
cv = CountVectorizer(token_pattern=TOKEN, lowercase=True, binary=True, min_df=10)
cv.fit(d["body_text"])
kata = np.array(cv.get_feature_names_out())


def persen(teks):
    return np.asarray(cv.transform(teks).mean(axis=0)).ravel() * 100


e = persen(d.loc[ke_ham, "body_text"])
lain = persen(df.loc[(y == "phishing") & (sub != F), "body_text"])
ham = persen(df.loc[y == "ham", "body_text"])
spam = persen(df.loc[y == "spam", "body_text"])
print("%-14s %7s %9s %6s %6s" % ("kata", "%error", "%phish_lain", "%ham", "%spam"))
for j in np.argsort(e - lain)[::-1][:25]:
    print("%-14s %7.1f %9.1f %6.1f %6.1f" % (kata[j], e[j], lain[j], ham[j], spam[j]))