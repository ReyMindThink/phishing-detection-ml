"""Tahap 5e-1: analisis NAMA header (diagnostik, bukan fitur). Hanya TRAIN.
Hanya nama header dan angka agregat; isi header tidak pernah dibaca/dicetak."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

URUTAN = ["ham", "spam", "phishing"]
NAZARIO = ["phishing0.mbox", "phishing1.mbox", "phishing2.mbox", "phishing3.mbox"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "n_headers", "n_received",
                          "header_names"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
sub = df["subset"].to_numpy()
df["n_unique"] = df["header_names"].str.split().str.len().fillna(0).astype(int)

cv = CountVectorizer(token_pattern=r"\S+", lowercase=False, binary=True, min_df=20)
X = cv.fit_transform(df["header_names"]).tocsr()
nama = np.array(cv.get_feature_names_out())
print("Nama header yang muncul di >= 20 email train:", len(nama))
pers = {k: np.asarray(X[y == k].mean(axis=0)).ravel() * 100 for k in URUTAN}
per_file = {s: np.asarray(X[sub == s].mean(axis=0)).ravel() * 100 for s in NAZARIO}


def baris(j):
    return "%-28s %6.1f %6.1f %7.1f" % (nama[j], pers["ham"][j], pers["spam"][j], pers["phishing"][j])


print("\n%-28s %6s %6s %7s" % ("=== 15 nama LEBIH tinggi di phishing", "%ham", "%spam", "%phish"))
gap = pers["phishing"] - pers["ham"]
for j in np.argsort(gap)[::-1][:15]:
    print(baris(j))
print("\n%-28s %6s %6s %7s" % ("=== 15 nama LEBIH tinggi di ham", "%ham", "%spam", "%phish"))
for j in np.argsort(gap)[:15]:
    print(baris(j))

cand = (pers["phishing"] >= 90) & (pers["ham"] < 20) & (pers["spam"] < 20)
print("\n=== Kandidat 'stempel pengumpul': >= 90%% phishing, < 20%% ham dan < 20%% spam: %d nama ===" % cand.sum())
print("%-28s %6s %6s %7s | %s" % ("nama", "%ham", "%spam", "%phish", "% per file (p0 p1 p2 p3)"))
for j in np.where(cand)[0]:
    print(baris(j) + " | " + " ".join("%5.1f" % per_file[s][j] for s in NAZARIO))

rentang = np.max([per_file[s] for s in NAZARIO], axis=0) - np.min([per_file[s] for s in NAZARIO], axis=0)
print("\n=== 12 nama dengan selisih terbesar antar empat file Nazario (poin persen) ===")
print("%-28s %6s | %s" % ("nama", "selisih", "% p0 p1 p2 p3"))
for j in np.argsort(rentang)[::-1][:12]:
    print("%-28s %6.1f | %s" % (nama[j], rentang[j], " ".join("%5.1f" % per_file[s][j] for s in NAZARIO)))

df["n_kand"] = np.asarray(X[:, np.where(cand)[0]].sum(axis=1)).ravel()
df["n_sisa"] = df["n_unique"] - df["n_kand"]
print("\n=== Uji lantai header (n_headers menghitung duplikat; n_unique = nama unik) ===")
print("%-16s %5s | %-13s | %-13s | %-13s | %s" % (
    "subset", "n", "n_headers", "n_unique", "n_received", "n_unique tanpa kandidat"))
print("%-16s %5s | %-13s | %-13s | %-13s | %s" % ("", "", "min/median", "min/median", "min/median", "min/median"))
for s in sorted(df["subset"].unique()):
    g = df[df["subset"] == s]
    f = lambda c: "%d/%.0f" % (g[c].min(), g[c].median())
    print("%-16s %5d | %-13s | %-13s | %-13s | %s%s" % (
        s, len(g), f("n_headers"), f("n_unique"), f("n_received"), f("n_sisa"),
        "  n<30 *" if len(g) < 30 else ""))

med = {k: df.loc[df["label"] == k, "n_unique"].median() for k in URUTAN}
med_sisa = df.loc[df["label"] == "phishing", "n_sisa"].median()
print("\nMedian n_unique: ham %.0f | spam %.0f | phishing %.0f | phishing tanpa kandidat %.0f" % (
    med["ham"], med["spam"], med["phishing"], med_sisa))
print("Selisih phishing-spam sebelum: %.1f | sesudah: %.1f" % (
    med["phishing"] - med["spam"], med_sisa - med["spam"]))