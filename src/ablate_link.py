"""Tahap 8-2: ablasi fitur link ditambahkan ke model teks (LogReg C=1). Data train saja.
Satu perubahan: + 10 fitur link (log1p + standardisasi). KONTROL: kolom link diacak antar baris.
Dinilai di OOF (5 lipatan) dan LOBO16 (purge). Hanya angka agregat. 3 bank gabungan = eksploratif."""
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

URUTAN = ["ham", "spam", "phishing"]
TARGET = 0.93
AMBANG_RESMI = 0.5040
MIN_N, MAX_MEREK = 30, 20
BANK3 = ["53.com", "bbt.com", "security.53.com"]
LINK = ["n_links", "n_link_domains", "n_link_mismatch", "n_link_ip", "n_link_userinfo",
        "n_link_punycode", "max_url_len", "max_host_labels", "n_images", "n_forms"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "sender_domain", "body_text"] + LINK)
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "group_final", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
df[LINK] = df[LINK].astype(float)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
grup = df["group_final"].to_numpy()
dom = df["sender_domain"].to_numpy()
ph = y == "phishing"
df_acak = df.copy()                                         # KONTROL: blok link diacak antar baris
df_acak[LINK] = df[LINK].sample(frac=1, random_state=42).to_numpy()
KONV = [0]


def buat(pakai_link):
    langkah = [("teks", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                        min_df=3, max_features=20000, sublinear_tf=True),
                "body_text")]
    if pakai_link:
        langkah.append(("link", Pipeline([("log", FunctionTransformer(np.log1p)),
                                          ("skala", StandardScaler())]), LINK))
    return Pipeline([("prep", ColumnTransformer(langkah)),
                     ("clf", LogisticRegression(max_iter=1000, random_state=42))])


def proba(d, pakai_link, tr, te):
    m = buat(pakai_link)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        m.fit(d.loc[tr, ["body_text"] + LINK], y[tr])
    KONV[0] += sum(issubclass(x.category, ConvergenceWarning) for x in w)
    urut = [list(m.classes_).index(c) for c in URUTAN]
    return m.predict_proba(d.loc[te, ["body_text"] + LINK])[:, urut]


def purge(te):
    return ph & np.isin(grup, np.unique(grup[te]))


cnt = pd.Series(dom[ph & (dom != "")]).value_counts()
merek = [d for d, n in cnt.items() if n >= MIN_N][:MAX_MEREK]
te3 = ph & np.isin(dom, BANK3)
assert len(merek) == 16 and te3.sum() == 212, (len(merek), te3.sum())  # CTRL


def nilai(nama, d, pakai_link):
    KONV[0] = 0
    oof = np.zeros((len(df), 3))
    for k in range(5):
        va = fold == k
        oof[va] = proba(d, pakai_link, ~va, va)
    p = oof[:, 2]
    t = np.sort(p[ph])[::-1][int(np.ceil(TARGET * ph.sum())) - 1]
    lain = np.where(oof[:, 0] >= oof[:, 1], "ham", "spam")
    pred = np.where(p >= t, "phishing", lain)
    tp, n_pred = int(((pred == "phishing") & ph).sum()), int((pred == "phishing").sum())
    hit = n = 0
    r53 = 0.0
    for dm in merek:
        te = ph & (dm == dom)
        h = int((proba(d, pakai_link, ~purge(te), te)[:, 2] >= t).sum())
        hit, n = hit + h, n + int(te.sum())
        if dm == "53.com":
            r53 = h / te.sum()
    r3 = float((proba(d, pakai_link, ~purge(te3), te3)[:, 2] >= t).mean())
    return dict(nama=nama, pr=average_precision_score(ph, p), t=t, tp=tp, n_pred=n_pred,
                prec=tp / n_pred, hit=hit, n=n, r53=r53, r3=r3, konv=KONV[0],
                fp_h=int(((pred == "phishing") & (y == "ham")).sum()),
                fp_s=int(((pred == "phishing") & (y == "spam")).sum()),
                mf1=f1_score(y, np.array(URUTAN)[oof.argmax(axis=1)], average="macro"),
                pl=np.array([average_precision_score(ph[fold == k], p[fold == k]) for k in range(5)]),
                rec_tetap=float(((p >= AMBANG_RESMI) & ph).sum() / ph.sum()),
                n_tetap=int((p >= AMBANG_RESMI).sum()))


b = nilai("teks saja (kontrol)", df, False)
assert abs(b["t"] - AMBANG_RESMI) < 5e-5 and (b["tp"], b["n_pred"]) == (2513, 2549), b  # CTRL
assert (b["hit"], b["n"]) == (1586, 1689), (b["hit"], b["n"])  # CTRL
print("KONTROL OK: teks saja = ambang 0,5040; precision 2513/2549; LOBO16 1586/1689")
l = nilai("teks + link", df, True)
a = nilai("teks + link ACAK (kontrol)", df_acak, True)

print("\nmodel | PR-AUC (per lipatan) | macroF1 | ambang | precision (tp/n) | FP ham/spam | "
      "LOBO16 (hit/n) | 53.com | 3 bank | recall pada 0,5040 (ditandai) | konvergensi")
for h in (b, l, a):
    print("%s | %.4f (%.3f-%.3f) | %.3f | %.4f | %.4f (%d/%d) | %d/%d | %.4f (%d/%d) | %.3f | %.3f | "
          "%.4f (%d) | %d" % (h["nama"], h["pr"], h["pl"].min(), h["pl"].max(), h["mf1"], h["t"],
                              h["prec"], h["tp"], h["n_pred"], h["fp_h"], h["fp_s"], h["hit"] / h["n"],
                              h["hit"], h["n"], h["r53"], h["r3"], h["rec_tetap"], h["n_tetap"], h["konv"]))
print("\nSelisih PR-AUC per lipatan (link - teks):", np.round(l["pl"] - b["pl"], 4))
print("Selisih PR-AUC per lipatan (acak - teks):", np.round(a["pl"] - b["pl"], 4))

syarat = [("precision naik >= 0,005", l["prec"] - b["prec"] >= 0.005, l["prec"] - b["prec"]),
          ("LOBO16 tidak turun > 0,01", l["hit"] / l["n"] - b["hit"] / b["n"] >= -0.01,
           l["hit"] / l["n"] - b["hit"] / b["n"]),
          ("salah tangkap ham tidak naik > 5", l["fp_h"] - b["fp_h"] <= 5, l["fp_h"] - b["fp_h"]),
          ("tanpa peringatan konvergensi", l["konv"] == 0, l["konv"])]
print("\nATURAN 8-0 (SEMUA harus terpenuhi):")
for nama, ok, v in syarat:
    print("  %-34s %s (selisih %+.4f)" % (nama, "OK" if ok else "GAGAL", v))
valid = abs(a["prec"] - b["prec"]) < 0.005 and a["konv"] == 0
print("KONTROL ACAK:", "valid (|selisih precision| < 0,005)" if valid
      else "TIDAK VALID: hasil tidak boleh ditafsirkan")
print("KEPUTUSAN:", "link MASUK model akhir" if all(s[1] for s in syarat) and valid
      else "model akhir tetap TEKS SAJA")