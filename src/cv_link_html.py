"""Tahap 5c-2: apakah fitur link menambah informasi di atas fitur bentuk,
DI DALAM email HTML? Hanya data train + 5 lipatan CV (splits.csv).
Test set dibuang. Hanya angka agregat."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SEED = 42
URUTAN = ["ham", "spam", "phishing"]
BENTUK_NUM = ["has_plain", "n_parts", "html_bytes", "plain_bytes", "n_headers",
              "n_received", "has_list_header", "has_mailman", "has_message_id",
              "has_x_mailer"]
BENTUK_CAT = ["content_type", "charset"]
TUJUAN = ["n_links", "n_link_domains", "n_link_mismatch", "n_link_ip",
          "n_link_userinfo", "n_link_punycode", "max_url_len", "max_host_labels"]
LETAK = ["n_images", "n_forms"]
SEMUA_NUM = BENTUK_NUM + TUJUAN + LETAK

KONFIG = {
    "S bentuk saja": (BENTUK_NUM, BENTUK_CAT),
    "S + tujuan": (BENTUK_NUM + TUJUAN, BENTUK_CAT),
    "S + letak": (BENTUK_NUM + LETAK, BENTUK_CAT),
    "S + tujuan + letak": (BENTUK_NUM + TUJUAN + LETAK, BENTUK_CAT),
    "tujuan saja": (TUJUAN, []),
    "letak saja": (LETAK, []),
    "tujuan + letak": (TUJUAN + LETAK, []),
}

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "has_html"] + SEMUA_NUM + BENTUK_CAT)
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[(df["split"] == "train") & (df["has_html"].astype(str) == "True")]
df = df.reset_index(drop=True)                      # TEST DIBUANG DI SINI
assert len(df) == 3474, len(df)
assert (df["fold"] >= 0).all()
df[SEMUA_NUM] = df[SEMUA_NUM].astype(float)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
ph = y == "phishing"
print("Email HTML train:", len(df), "| per kelas:", df["label"].value_counts()[URUTAN].to_dict())
print("PR-AUC phishing acak di subset ini = %.3f" % ph.mean())


def jalankan(num, cat):
    """5 lipatan: latih di 4, prediksi di 1. Kembalikan P(phishing) out-of-fold."""
    langkah = [("num", "passthrough", num)]
    if cat:
        langkah.append(("cat", OneHotEncoder(handle_unknown="infrequent_if_exist",
                                             min_frequency=20, sparse_output=False), cat))
    oof = np.zeros(len(df))
    for k in range(5):
        va = fold == k
        model = Pipeline([("prep", ColumnTransformer(langkah)),
                          ("clf", HistGradientBoostingClassifier(random_state=SEED))])
        model.fit(df.loc[~va, num + cat], y[~va])
        kolom = list(model.classes_).index("phishing")
        oof[va] = model.predict_proba(df.loc[va, num + cat])[:, kolom]
    return oof


def per_lipatan(p):
    return np.array([average_precision_score(ph[fold == k], p[fold == k]) for k in range(5)])


hasil = {nama: jalankan(num, cat) for nama, (num, cat) in KONFIG.items()}
dasar = per_lipatan(hasil["S bentuk saja"])

print("\n%-20s %8s  %-13s %10s %10s" % ("model", "PR-AUC", "per lipatan", "AUC vs spam", "AUC vs ham"))
for nama, p in hasil.items():
    pl = per_lipatan(p)
    m_sp, m_ha = y != "ham", y != "spam"
    print("%-20s %8.3f  %.3f-%.3f   %10.3f %10.3f" % (
        nama, average_precision_score(ph, p), pl.min(), pl.max(),
        roc_auc_score(ph[m_sp], p[m_sp]), roc_auc_score(ph[m_ha], p[m_ha])))

print("\nSelisih PR-AUC per lipatan terhadap 'S bentuk saja' (berpasangan):")
for nama in ["S + tujuan", "S + letak", "S + tujuan + letak"]:
    d = per_lipatan(hasil[nama]) - dasar
    print("%-20s rata-rata=%+.4f  per lipatan=%s  membaik di %d dari 5 lipatan"
          % (nama, d.mean(), np.round(d, 4).tolist(), (d > 0).sum()))
