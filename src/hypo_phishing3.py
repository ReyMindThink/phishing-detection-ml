"""Tahap 6-6: uji dua hipotesis dari 6-5 (merek dan kata naratif). Hanya TRAIN (splits.csv).
Test dibuang. Hanya angka agregat dan nama domain merek; tanpa isi email."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
URUTAN = ["ham", "spam", "phishing"]
F = "phishing3.mbox"
TOP3 = ["53.com", "bbt.com", "security.53.com"]
DOMAIN = TOP3 + ["ebay.com", "bankofamerica.com", "paypal.com", "suntrust.com"]
NARASI = ["she", "his", "her", "him", "said", "looked", "came", "hand", "little"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "sender_domain", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold", "group_final"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
sub = df["subset"].to_numpy()
fold = df["fold"].to_numpy()
g = df["group_final"].to_numpy()
dom = df["sender_domain"].to_numpy()
ph = y == "phishing"
p3 = sub == F
oth = ph & ~p3
top3 = np.isin(dom, TOP3)


def buat_model():
    return Pipeline([("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3,
                                               max_features=20000, sublinear_tf=True)),
                     ("clf", LogisticRegression(max_iter=1000, random_state=42))])


oof = np.empty(len(df), dtype=object)
for k in range(5):
    va = fold == k
    m = buat_model()
    m.fit(df.loc[~va, "body_text"], y[~va])
    oof[va] = m.predict(df.loc[va, "body_text"])
diag = [int((oof[y == c] == c).sum()) for c in URUTAN]
assert diag == [3245, 1317, 2584], diag

te = np.where(p3)[0]
tr = np.where(~p3)[0]
m = buat_model()
m.fit(df["body_text"].iloc[tr], y[tr])
lofo = np.empty(len(df), dtype=object)
lofo[te] = m.predict(df["body_text"].iloc[te])
n_ham, n_spam = int((lofo[te] == "ham").sum()), int((lofo[te] == "spam").sum())
assert (n_ham, n_spam) == (249, 10), (n_ham, n_spam)
print("KONTROL OK: OOF 3245/1317/2584 dan LOFO phishing3 ke ham %d, ke spam %d" % (n_ham, n_spam))


def rec(mask, pred):
    return (pred[mask] == "phishing").mean() if mask.sum() else float("nan")


print("\n=== A. Hipotesis merek: phishing3, recall OOF (CV acak) vs LOFO, per domain pengirim ===")
print("%-20s %6s %7s %10s %10s %9s %9s" % ("domain", "n_p3", "n_grup", "n_p_lain", "n_ham_spam",
                                           "rec_OOF", "rec_LOFO"))
for d in DOMAIN:
    mk = p3 & (dom == d)
    if mk.sum() == 0:
        print("%-20s %6d" % (d, 0))
        continue
    print("%-20s %6d %7d %10d %10d %9.3f %9.3f" % (
        d, mk.sum(), len(set(g[mk])), (oth & (dom == d)).sum(), (~ph & (dom == d)).sum(),
        rec(mk, oof), rec(mk, lofo)))
for nama, mk in [("TOP3 digabung", p3 & top3), ("phishing3 domain lain", p3 & ~top3)]:
    print("%-20s %6d %7d %10s %10s %9.3f %9.3f" % (
        nama, mk.sum(), len(set(g[mk])), "", "", rec(mk, oof), rec(mk, lofo)))

cv = CountVectorizer(token_pattern=TOKEN, lowercase=True, binary=True, vocabulary=NARASI)
flag = np.asarray(cv.transform(df["body_text"]).sum(axis=1)).ravel() >= 3

print("\n=== B. Hipotesis kata naratif: email memuat >= 3 dari 9 kata (%s) ===" % " ".join(NARASI))
kel = [("phishing3 domain TOP3", p3 & top3), ("phishing3 domain lain", p3 & ~top3),
       ("phishing file lain", oth), ("ham", y == "ham"), ("spam", y == "spam")]
print("%-24s %6s %8s" % ("kelompok", "n", "%flag"))
for nama, mk in kel:
    print("%-24s %6d %8.1f" % (nama, mk.sum(), flag[mk].mean() * 100))

print("\n=== C. phishing3: recall menurut domain TOP3 x flag naratif ===")
print("%-28s %6s %9s %9s" % ("sel", "n", "rec_OOF", "rec_LOFO"))
for t_nama, tm in [("TOP3", top3), ("domain lain", ~top3)]:
    for f_nama, fm in [("flag", flag), ("tanpa flag", ~flag)]:
        mk = p3 & tm & fm
        print("%-28s %6d %9.3f %9.3f" % (t_nama + " + " + f_nama, mk.sum(), rec(mk, oof), rec(mk, lofo)))

err = p3 & (lofo != "phishing")
print("\n=== D. Kesalahan LOFO phishing3 (ke ham atau spam): n=%d ===" % err.sum())
print("di domain TOP3: %d (%.1f%%) | dengan flag naratif: %d (%.1f%%)" % (
    (err & top3).sum(), (err & top3).sum() / err.sum() * 100,
    (err & flag).sum(), (err & flag).sum() / err.sum() * 100))
print("TOP3 atau flag: %d | TIDAK TERJELASKAN (bukan TOP3 dan tanpa flag): %d" % (
    (err & (top3 | flag)).sum(), (err & ~top3 & ~flag).sum()))