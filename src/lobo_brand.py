"""Tahap 7-3: leave-one-brand-out (LOBO) dengan purge, LogReg vs RandomForest.
Merek = sender_domain phishing, HANYA untuk membagi data (BUKAN fitur). Data train saja.
Hanya angka agregat. Uji EKSPLORATIF: daftar merek dipilih dari ukuran di train."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]
TARGET = 0.93        # keputusan 7-1
MIN_N = 30           # merek dengan < 30 email phishing tidak diuji
MAX_MEREK = 20

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "sender_domain", "body_text"])
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "group_final", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
grup = df["group_final"].to_numpy()
dom = df["sender_domain"].to_numpy()
ph = y == "phishing"

MODEL = {
    "LogReg": lambda: LogisticRegression(max_iter=1000, random_state=42),
    "RF": lambda: RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
}


def proba(buat, tr, te):
    m = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                  min_df=3, max_features=20000, sublinear_tf=True)),
        ("clf", buat()),
    ])
    m.fit(df.loc[tr, "body_text"], y[tr])
    urut = [list(m.classes_).index(c) for c in URUTAN]
    return m.predict_proba(df.loc[te, "body_text"])[:, urut]


oof, t = {}, {}
for nama, buat in MODEL.items():
    oof[nama] = np.zeros((len(df), 3))
    for k in range(5):
        va = fold == k
        oof[nama][va] = proba(buat, ~va, va)
    t[nama] = np.sort(oof[nama][ph, 2])[::-1][int(np.ceil(TARGET * ph.sum())) - 1]
    print("ambang resmi %-6s = %.4f" % (nama, t[nama]))
assert abs(t["LogReg"] - 0.5040) < 5e-5, t["LogReg"]  # CTRL: sama dengan 7-1
print("KONTROL 1 OK: ambang LogReg 0,5040 (RF harus sekitar 0,5033)")

m3 = df["subset"].str.contains("phishing3").to_numpy() & ph
assert m3.sum() == 1404, sorted(df.loc[ph, "subset"].unique())  # CTRL
p3 = proba(MODEL["LogReg"], ~m3, m3).argmax(axis=1)
assert [(p3 == i).sum() for i in range(3)] == [249, 10, 1145], [(p3 == i).sum() for i in range(3)]  # CTRL
print("KONTROL 2 OK: LOFO phishing3 = 249 ke ham, 10 ke spam, 1145 terdeteksi (sama dengan 6-4)")

cnt = pd.Series(dom[ph & (dom != "")]).value_counts()
merek = [d for d, n in cnt.items() if n >= MIN_N][:MAX_MEREK]
print("\nMerek diuji: %d (n >= %d email phishing di train)" % (len(merek), MIN_N))
print("%-22s %4s %6s | %-13s | %-13s" % ("merek", "n", "purge+", "LogReg OOF>LOBO", "RF OOF>LOBO"))
tot = {"n": 0, **{(a, b): 0 for a in MODEL for b in ("oof", "lobo")}}
for d in merek:
    te = ph & (dom == d)
    buang = ph & np.isin(grup, np.unique(grup[te]))     # purge: grup yang sama ikut dibuang
    n = int(te.sum())
    baris = []
    for nama, buat in MODEL.items():
        h_lobo = int((proba(buat, ~buang, te)[:, 2] >= t[nama]).sum())
        h_oof = int((oof[nama][te, 2] >= t[nama]).sum())
        tot[(nama, "lobo")] += h_lobo
        tot[(nama, "oof")] += h_oof
        baris.append("%.3f > %.3f" % (h_oof / n, h_lobo / n))
    tot["n"] += n
    print("%-22s %4d %6d | %-15s | %-15s" % (d + ("*" if n < 30 else ""), n,
                                          int(buang.sum() - n), baris[0], baris[1]))
print("\nGABUNGAN %d merek (n=%d), recall pada ambang resmi:" % (len(merek), tot["n"]))
for nama in MODEL:
    print("  %-7s OOF %.3f -> LOBO %.3f" % (nama, tot[(nama, "oof")] / tot["n"],
                                           tot[(nama, "lobo")] / tot["n"]))