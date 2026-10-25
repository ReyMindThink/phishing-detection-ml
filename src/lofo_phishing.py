"""Tahap 6-4: leave-one-file-out (LOFO) untuk phishing. Hanya TRAIN (splits.csv).
Test dibuang. Hanya angka agregat (tanpa isi email)."""
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SEED = 42
TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
URUTAN = ["ham", "spam", "phishing"]
FILES = ["phishing0.mbox", "phishing1.mbox", "phishing2.mbox", "phishing3.mbox", "20051114.mbox"]
BENTUK_NUM = ["has_html", "has_plain", "n_parts", "html_bytes", "plain_bytes", "n_headers",
              "n_received", "has_list_header", "has_mailman", "has_message_id", "has_x_mailer"]
BENTUK_CAT = ["content_type", "charset"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "body_text"] + BENTUK_NUM + BENTUK_CAT)
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "split", "fold", "group_final"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
df[BENTUK_NUM] = df[BENTUK_NUM].astype(float)
y = df["label"].to_numpy()
sub = df["subset"].to_numpy()
fold = df["fold"].to_numpy()
g = df["group_final"].to_numpy()
ph = y == "phishing"


def model_teks():
    return Pipeline([("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3,
                                               max_features=20000, sublinear_tf=True)),
                     ("clf", LogisticRegression(max_iter=1000, random_state=SEED))])


def model_bentuk():
    return Pipeline([("p", ColumnTransformer([
        ("n", "passthrough", BENTUK_NUM),
        ("c", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20,
                            sparse_output=False), BENTUK_CAT)])),
        ("m", HistGradientBoostingClassifier(random_state=SEED))])


def prediksi(jenis, tr, te):
    if jenis == "teks":
        m, X = model_teks(), df["body_text"]
    else:
        m, X = model_bentuk(), df[BENTUK_NUM + BENTUK_CAT]
    m.fit(X.iloc[tr], y[tr])
    return m.predict(X.iloc[te])


JENIS = ["teks", "bentuk"]
oof = {j: np.empty(len(df), dtype=object) for j in JENIS}
for k in range(5):
    va, tr = np.where(fold == k)[0], np.where(fold != k)[0]
    for j in JENIS:
        oof[j][va] = prediksi(j, tr, va)
diag = [int((oof["teks"][y == c] == c).sum()) for c in URUTAN]
assert diag == [3245, 1317, 2584], diag
print("KONTROL OK: diagonal OOF teks = 3245/1317/2584 (sama dengan 5d-2)")
print("Recall phishing OOF seluruh train: teks %.3f | bentuk %.3f\n" % (
    (oof["teks"][ph] == "phishing").mean(), (oof["bentuk"][ph] == "phishing").mean()))

lintas = pd.DataFrame({"g": g[ph], "s": sub[ph]}).groupby("g")["s"].nunique()
print("Grup phishing: %d | muncul di >= 2 file: %d (%.1f%%)\n" % (
    len(lintas), (lintas >= 2).sum(), (lintas >= 2).mean() * 100))

baris = []
for F in FILES:
    te = np.where(sub == F)[0]
    assert (y[te] == "phishing").all()
    tr = np.where(sub != F)[0]
    g_lain = set(g[ph & (sub != F)])
    bersih = np.array([gi not in g_lain for gi in g[te]])
    r = {"file": F + (" *" if len(te) < 30 else ""), "n": len(te),
         "n_bersih": int(bersih.sum()), "%bersih": round(bersih.mean() * 100, 1)}
    for j in JENIS:
        p = prediksi(j, tr, te)
        salah = Counter(p[p != "phishing"])
        r[j + "_OOF"] = (oof[j][te] == "phishing").mean()
        r[j + "_LOFO"] = (p == "phishing").mean()
        r[j + "_LOFO_bersih"] = (p[bersih] == "phishing").mean() if bersih.any() else np.nan
        r[j + "_salah->ham/spam"] = "%d/%d" % (salah.get("ham", 0), salah.get("spam", 0))
    baris.append(r)

t = pd.DataFrame(baris).set_index("file")
print("=== Recall phishing (tebakan terbanyak): OOF 5 lipatan vs LOFO ===")
print(t.round(3).to_string())

besar = t.index[:4]
for j in JENIS:
    d = (t.loc[besar, j + "_OOF"] - t.loc[besar, j + "_LOFO"])
    w = t.loc[besar, "n"]
    print("\nPenurunan recall (OOF - LOFO), 4 file besar, model %s: per file %s | rata-rata %.3f | berbobot %.3f" % (
        j, d.round(3).tolist(), d.mean(), (d * w).sum() / w.sum()))