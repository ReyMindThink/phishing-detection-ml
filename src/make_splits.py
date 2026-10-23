"""Split final per kelompok: test set (~20%) + 5 lipatan CV pada sisanya.

Hanya angka agregat. Menyimpan data/processed/splits.csv (hash + kelompok +
bagian), tanpa isi email.
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.model_selection import StratifiedGroupKFold

SEED = 42  # dipilih SEKALI, tidak diubah setelah melihat hasil
ARTEFAK = {"spamassassin.taint.org"}
JEMBATAN = {"barrera.org", "evergo.net", "pobox.com", "mithral.com", "slack.net"}
URUTAN = ["ham", "spam", "phishing"]
OUT = "data/processed/splits.csv"

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "sender_domain",
                          "group_id", "source_file"])
n = len(df)
assert df["content_hash"].is_unique

# Domain dikecualikan = generik (muncul di >1 kelas) + artefak + jembatan.
per_dom = df[df["sender_domain"] != ""].groupby("sender_domain")["label"].nunique()
generik = set(per_dom[per_dom > 1].index) | ARTEFAK
dikecualikan = generik | JEMBATAN

# Kunci domain: hanya ham/spam dengan domain layak. Phishing tidak dipakai.
dom = df["sender_domain"].where(
    (df["sender_domain"] != "")
    & ~df["sender_domain"].isin(dikecualikan)
    & (df["label"] != "phishing"))


def tepi_bintang(kunci):
    pertama = pd.Series(np.arange(n)).groupby(kunci).transform("min")
    ok = pertama.notna().to_numpy()
    return np.arange(n)[ok], pertama[ok].astype(int).to_numpy()


r, c = [], []
for kunci in (df["group_id"], dom):
    a, b = tepi_bintang(kunci)
    r.append(a)
    c.append(b)
r, c = np.concatenate(r), np.concatenate(c)
G = coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
df["group_final"] = connected_components(G, directed=False)[1]
print("Total grup final:", df["group_final"].nunique())

# --- Tahap 1: test set. Tahap 2: 5 lipatan CV pada sisanya ---
y, g, idx = df["label"].to_numpy(), df["group_final"].to_numpy(), np.arange(n)

sisa, uji = next(StratifiedGroupKFold(5, shuffle=True, random_state=SEED).split(idx, y, g))
df["split"] = "train"
df.loc[uji, "split"] = "test"
df["fold"] = -1
for k, (_, val) in enumerate(
        StratifiedGroupKFold(5, shuffle=True, random_state=SEED).split(sisa, y[sisa], g[sisa])):
    df.loc[sisa[val], "fold"] = k

# --- Pengecekan wajib ---
assert (df.groupby("group_final")["split"].nunique() == 1).all(), "grup terbelah train/test"
tr = df[df["split"] == "train"]
assert (tr.groupby("group_final")["fold"].nunique() == 1).all(), "grup terbelah antar-fold"
print("OK: tidak ada grup yang terbelah.")

df["bagian"] = np.where(df["split"] == "test", "test", "cv" + df["fold"].astype(str))
jml = pd.crosstab(df["bagian"], df["label"])[URUTAN]
print("\nJumlah email per bagian:")
print(jml.to_string())
print("\n% kelas per bagian (bandingkan dengan baris 'semua'):")
persen = (jml.div(jml.sum(axis=1), axis=0) * 100).round(1)
persen.loc["semua"] = (df["label"].value_counts(normalize=True)[URUTAN] * 100).round(1)
print(persen.to_string())

# --- Tumpang tindih domain pengirim train vs test ---
te = df[df["split"] == "test"]
print("\nDomain pengirim di test yang JUGA ada di train (per kelas):")
for label in URUTAN:
    t = te[(te["label"] == label) & (te["sender_domain"] != "")]
    sudah = t["sender_domain"].isin(set(tr[tr["label"] == label]["sender_domain"]))
    layak = ~t["sender_domain"].isin(dikecualikan)
    print(f"  {label:9} berdomain={len(t):4} | semua: {sudah.mean() * 100:5.1f}% "
          f"| hanya domain layak: {(sudah & layak).sum()} dari {int(layak.sum())}")
    if label != "phishing":
        assert not (sudah & layak).any(), "domain layak bocor ke test"

ph = df[df["label"] == "phishing"]
print("\n% phishing per file Nazario (train vs test):")
print((pd.crosstab(ph["split"], ph["source_file"], normalize="index") * 100).round(1).to_string())

df[["content_hash", "label", "group_final", "split", "fold"]].to_csv(OUT, index=False)
print("\nTersimpan:", OUT)