"""Uji artefak awal: seberapa jauh model 'curang' (hanya bentuk email) menebak kelas?

Hanya data train dan 5 lipatan CV dari splits.csv. Test set TIDAK disentuh.
Hanya angka agregat.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SEED = 42
URUTAN = ["ham", "spam", "phishing"]

# Kelompok fitur bentuk: (numerik, kategori). n_urls dan sender_domain SENGAJA tidak ada.
KELOMPOK = {
    "html": (["has_html", "has_plain", "n_parts", "html_bytes", "plain_bytes"], ["content_type"]),
    "header": (["n_headers", "n_received", "has_list_header", "has_mailman",
                "has_message_id", "has_x_mailer"], []),
    "charset": ([], ["charset"]),
}
NUM_SEMUA = sum((v[0] for v in KELOMPOK.values()), [])
CAT_SEMUA = sum((v[1] for v in KELOMPOK.values()), [])

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "source", "subset"] + NUM_SEMUA + CAT_SEMUA)
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"

df = df[df["split"] == "train"].reset_index(drop=True)   # TEST DIBUANG DI SINI
assert (df["fold"] >= 0).all()
df[NUM_SEMUA] = df[NUM_SEMUA].astype(float)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
print("Baris train:", len(df), "| per kelas:", df["label"].value_counts()[URUTAN].to_dict())
print("Baseline: akurasi tebak-kelas-terbanyak = %.3f | PR-AUC phishing acak = %.3f"
      % (df["label"].value_counts(normalize=True).max(), (y == "phishing").mean()))


def jalankan(num, cat):
    """5 lipatan: latih di 4, prediksi di 1. Kembalikan probabilitas out-of-fold."""
    fitur = num + cat
    langkah = []
    if num:
        langkah.append(("num", "passthrough", num))
    if cat:
        langkah.append(("cat", OneHotEncoder(handle_unknown="infrequent_if_exist",
                                             min_frequency=20, sparse_output=False), cat))
    oof = np.zeros((len(df), 3))
    for k in range(5):
        va = fold == k
        model = Pipeline([("prep", ColumnTransformer(langkah)),
                          ("clf", HistGradientBoostingClassifier(random_state=SEED))])
        model.fit(df.loc[~va, fitur], y[~va])
        urut = [list(model.classes_).index(c) for c in URUTAN]
        oof[va] = model.predict_proba(df.loc[va, fitur])[:, urut]
    return oof


def laporan(nama, oof):
    pred = np.array(URUTAN)[oof.argmax(axis=1)]
    ph = oof[:, 2]
    per_fold = [average_precision_score(y[fold == k] == "phishing", ph[fold == k]) for k in range(5)]
    print(f"{nama:22} macroF1={f1_score(y, pred, average='macro'):.3f}  "
          f"akurasi={accuracy_score(y, pred):.3f}  "
          f"PR-AUC phishing={average_precision_score(y == 'phishing', ph):.3f}  "
          f"(per lipatan {min(per_fold):.3f}-{max(per_fold):.3f})")
    return pred


print("\n=== Model 'curang' (hanya bentuk email), prediksi out-of-fold ===")
pred_semua = None
for nama, (num, cat) in [("SEMUA fitur bentuk", (NUM_SEMUA, CAT_SEMUA)),
                         ("hanya kelompok html", KELOMPOK["html"]),
                         ("hanya kelompok header", KELOMPOK["header"]),
                         ("hanya kelompok charset", KELOMPOK["charset"])]:
    pred = laporan(nama, jalankan(num, cat))
    if pred_semua is None:
        pred_semua = pred

print("\nConfusion matrix SEMUA fitur bentuk (baris = benar, kolom = tebakan):")
print(pd.DataFrame(confusion_matrix(y, pred_semua, labels=URUTAN),
                   index=URUTAN, columns=URUTAN).to_string())

print("\n=== ID sumber: bukan model, hanya bukti ===")
print(pd.crosstab(df["source"], df["label"]).to_string())
campur = (df.groupby("subset")["label"].nunique() > 1).sum()
print("Subset yang berisi lebih dari satu label:", int(campur))

# --- Lanjutan: fitur mana yang jadi jalan pintas? ---
tp = ((pred_semua == "phishing") & (y == "phishing")).sum()
print("\nPhishing (model curang, tebakan terbanyak): precision=%.3f recall=%.3f"
      % (tp / (pred_semua == "phishing").sum(), tp / (y == "phishing").sum()))


def pr_auc(num, cat):
    return average_precision_score(y == "phishing", jalankan(num, cat)[:, 2])


print("\n=== Satu fitur SENDIRIAN (PR-AUC phishing; acak = 0.363) ===")
hasil = {f: pr_auc([f], []) for f in NUM_SEMUA}
hasil.update({f: pr_auc([], [f]) for f in CAT_SEMUA})
for f, v in sorted(hasil.items(), key=lambda kv: -kv[1]):
    print(f"  {f:18} {v:.3f}")

print("\n=== SEMUA fitur kecuali satu kelompok ===")
for nama, (num, cat) in KELOMPOK.items():
    sisa_num = [f for f in NUM_SEMUA if f not in num]
    sisa_cat = [f for f in CAT_SEMUA if f not in cat]
    print(f"  tanpa {nama:8} PR-AUC phishing={pr_auc(sisa_num, sisa_cat):.3f}")