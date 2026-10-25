"""Tahap 5e-2: ablasi cap pengumpul pada n_headers. Hanya TRAIN + 5 lipatan (splits.csv).
header_names dipakai HANYA untuk diagnostik ini (bukan fitur). Hanya angka agregat."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SEED = 42
URUTAN = ["ham", "spam", "phishing"]
HTML_NUM = ["has_html", "has_plain", "n_parts", "html_bytes", "plain_bytes"]
HDR_NUM = ["n_headers", "n_received", "has_list_header", "has_mailman",
           "has_message_id", "has_x_mailer"]
NUM = HTML_NUM + HDR_NUM
CAT = ["content_type", "charset"]
HDR_CAT = []
CAP_K1 = {"status", "x-original-to", "x-uid", "lines", "content-length"}
CAP_K2 = CAP_K1 | {"x-status", "x-keywords"}

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "header_names"] + NUM + CAT)
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
assert (df["fold"] >= 0).all()
df[NUM] = df[NUM].astype(float)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
ph = y == "phishing"

nama = df["header_names"].str.split().map(set)
n1 = nama.map(lambda s: len(s & CAP_K1) + sum(1 for n in s if n.startswith("x-spam-")))
n2 = n1 + nama.map(lambda s: len(s & {"x-status", "x-keywords"}))
df["n_headers_adj1"] = df["n_headers"] - n1
df["n_headers_adj2"] = df["n_headers"] - n2
assert (df["n_headers_adj1"] >= 0).all() and (df["n_headers_adj2"] >= 0).all()

print("Median n_headers per kelas (asli | K1 | K2):")
for k in URUTAN:
    m = y == k
    print("  %-9s %5.1f | %5.1f | %5.1f   (cap rata-rata K1=%.2f, K2=%.2f)" % (
        k, df.loc[m, "n_headers"].median(), df.loc[m, "n_headers_adj1"].median(),
        df.loc[m, "n_headers_adj2"].median(), n1[m].mean(), n2[m].mean()))


def jalankan(num, cat):
    fitur = num + cat
    langkah = [("num", "passthrough", num)]
    if cat:
        langkah.append(("cat", OneHotEncoder(handle_unknown="infrequent_if_exist",
                                             min_frequency=20, sparse_output=False), cat))
    oof = np.zeros(len(df))
    for k in range(5):
        va = fold == k
        model = Pipeline([("prep", ColumnTransformer(langkah)),
                          ("clf", HistGradientBoostingClassifier(random_state=SEED))])
        model.fit(df.loc[~va, fitur], y[~va])
        oof[va] = model.predict_proba(df.loc[va, fitur])[:, list(model.classes_).index("phishing")]
    return oof


def ganti(daftar, baru):
    return [baru if f == "n_headers" else f for f in daftar]


def lapor(nama_uji, num, cat, acuan=None):
    p = jalankan(num, cat)
    pl = [average_precision_score(ph[fold == k], p[fold == k]) for k in range(5)]
    skor = average_precision_score(ph, p)
    cat_ = "" if acuan is None else "  (kontrol: %.3f -> %s)" % (acuan, "OK" if round(skor, 3) == acuan else "GAGAL")
    print("%-34s PR-AUC phishing=%.3f (per lipatan %.3f-%.3f)%s" % (
        nama_uji, skor, min(pl), max(pl), cat_))
    return skor


print("\n=== SEMUA fitur bentuk (acak = %.3f) ===" % ph.mean())
a = lapor("asli", NUM, CAT, 0.995)
b = lapor("n_headers -> adj K1", ganti(NUM, "n_headers_adj1"), CAT)
c = lapor("n_headers -> adj K2", ganti(NUM, "n_headers_adj2"), CAT)
print("\n=== Kelompok header saja ===")
a2 = lapor("asli", HDR_NUM, HDR_CAT, 0.979)
b2 = lapor("n_headers -> adj K1", ganti(HDR_NUM, "n_headers_adj1"), HDR_CAT)
c2 = lapor("n_headers -> adj K2", ganti(HDR_NUM, "n_headers_adj2"), HDR_CAT)
print("\n=== n_headers SENDIRIAN ===")
a3 = lapor("asli", ["n_headers"], [], 0.803)
b3 = lapor("adj K1", ["n_headers_adj1"], [])
c3 = lapor("adj K2", ["n_headers_adj2"], [])
print("\nSelisih terhadap asli (K1 | K2): semua %+.3f | %+.3f ; header saja %+.3f | %+.3f ; "
      "sendirian %+.3f | %+.3f" % (b - a, c - a, b2 - a2, c2 - a2, b3 - a3, c3 - a3))