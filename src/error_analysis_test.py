"""Tahap 8-6: analisis kesalahan pada test (EKSPLORATIF; hanya angka agregat, tanpa isi email).

Membaca data/processed/test_proba.csv (hasil 8-5) TANPA menjalankan model. Tidak mengubah model atau ambang.
n kecil (36 phishing lolos, 12 salah tangkap): semua perbedaan = HIPOTESIS. Rencana dikunci di dokumen sebelum jalan.
Jalankan: python src/error_analysis_test.py
"""
import json
import os
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

KONTROL = os.environ.get("UJI_ALUR_SINTETIS") != "1"    # "1" HANYA untuk menguji alur pada data sintetis
URUTAN = ["ham", "spam", "phishing"]
t = json.loads(Path("docs/model_manifest.json").read_text(encoding="utf-8"))["ambang"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "source_file", "body_text", "sender_domain",
                          "has_html", "n_attachments", "n_links"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
tr = df[df["split"] == "train"].reset_index(drop=True)
te = pd.read_csv("data/processed/test_proba.csv").merge(
    df.drop(columns=["label"]), on="content_hash", how="left", validate="one_to_one")
assert (te["split"] == "test").all() and len(te) == (1860 if KONTROL else len(te))
cm = pd.crosstab(te["label"], te["putusan"]).reindex(index=URUTAN, columns=URUTAN, fill_value=0).to_numpy()
if KONTROL:
    assert cm.tolist() == [[807, 12, 3], [17, 336, 9], [23, 13, 640]], cm.tolist()
    print("KONTROL OK: confusion 8-5 tereproduksi dari test_proba.csv")

te["has_html"] = te["has_html"].astype(str) == "True"
te["lampiran"] = pd.to_numeric(te["n_attachments"], errors="coerce").fillna(0) > 0
te["link"] = pd.to_numeric(te["n_links"], errors="coerce").fillna(0) > 0
dom_train = set(tr["sender_domain"]) - {""}
te["asing"] = (te["sender_domain"] != "") & ~te["sender_domain"].isin(dom_train)
te["kata"] = te["body_text"].str.count(r"\b[a-zA-Z]{3,}\b")
vec = TfidfVectorizer(min_df=2, sublinear_tf=True, max_features=50000)
Xtr = vec.fit_transform(tr["body_text"])
te["cos"] = (vec.transform(te["body_text"]) @ Xtr.T.tocsc()).toarray().max(axis=1)

y, pr = te["label"], te["putusan"]
kelompok = {"phishing LOLOS": (y == "phishing") & (pr != "phishing"),
            "phishing tertangkap": (y == "phishing") & (pr == "phishing"),
            "ham salah tangkap": (y == "ham") & (pr == "phishing"),
            "ham tidak ditandai": (y == "ham") & (pr != "phishing"),
            "spam salah tangkap": (y == "spam") & (pr == "phishing"),
            "spam tidak ditandai": (y == "spam") & (pr != "phishing")}
print("\nKelompok (n; * bila n < 30): kata (>= 3 huruf) median | HTML | lampiran | link > 0 | domain asing | cosine maks ke train median")
for nama, m in kelompok.items():
    d, n = te[m], int(m.sum())
    if n:
        print("%-20s n=%-4d%s kata %4.0f | HTML %d/%d | lampiran %d/%d | link %d/%d | domain asing %d/%d | cos %.3f" % (
            nama, n, "*" if n < 30 else " ", d["kata"].median(), d["has_html"].sum(), n, d["lampiran"].sum(), n,
            d["link"].sum(), n, d["asing"].sum(), n, d["cos"].median()))

lolos = te[kelompok["phishing LOLOS"]]
print("\nPhishing LOLOS (n=%d): putusan %s" % (len(lolos), lolos["putusan"].value_counts().to_dict()))
pita = pd.cut(lolos["p_phishing"], [0, 0.1, 0.3, t], right=False).value_counts().sort_index()
print("  P(phishing) per pita:", {str(k): int(v) for k, v in pita.items()})
print("  per file:", lolos["source_file"].value_counts().to_dict())
g = lolos["group_final"].value_counts()
print("  %d email lolos tersebar di %d grup; grup terbanyak %d email" % (len(lolos), len(g), g.iloc[0] if len(g) else 0))
for nama in ("ham salah tangkap", "spam salah tangkap"):
    f = te[kelompok[nama]]
    print("%s (n=%d): subset %s | median P(phishing) %.3f" % (nama, len(f), f["subset"].value_counts().to_dict(),
                                                                f["p_phishing"].median() if len(f) else float("nan")))