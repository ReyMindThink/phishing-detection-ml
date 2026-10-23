"""Cari domain 'jembatan' yang menyambung grup ham raksasa (skenario C).

Hanya nama domain dan angka agregat. Tidak menampilkan isi email.
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ARTEFAK = {"spamassassin.taint.org"}
TARGET = 0.05   # grup ham terbesar harus < 5% dari kelas ham

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["label", "sender_domain", "group_id"])
n = len(df)

per_dom = df[df["sender_domain"] != ""].groupby("sender_domain")["label"].nunique()
generik = set(per_dom[per_dom > 1].index) | ARTEFAK


def tepi_bintang(kunci):
    """Hubungkan tiap baris ke baris pertama yang punya kunci sama."""
    pertama = pd.Series(np.arange(n)).groupby(kunci).transform("min")
    ok = pertama.notna().to_numpy()
    return np.arange(n)[ok], pertama[ok].astype(int).to_numpy()


def grup_c(buang=()):
    """Skenario C: grup teks + domain (ham/spam saja), domain 'buang' diabaikan."""
    dom = df["sender_domain"].where(
        (df["sender_domain"] != "")
        & ~df["sender_domain"].isin(generik | set(buang))
        & (df["label"] != "phishing"))
    r, c = [], []
    for kunci in (df["group_id"], dom):
        a, b = tepi_bintang(kunci)
        r.append(a)
        c.append(b)
    r, c = np.concatenate(r), np.concatenate(c)
    G = coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
    return connected_components(G, directed=False)[1]


# Derajat domain = berapa domain LAIN yang berbagi grup teks dengannya (ham saja).
ham = df[(df["label"] == "ham") & (df["sender_domain"] != "")
         & ~df["sender_domain"].isin(generik)]
tetangga = {}
for ds in ham.groupby("group_id")["sender_domain"].agg(lambda s: sorted(set(s))):
    if len(ds) > 1:
        for d in ds:
            tetangga.setdefault(d, set()).update(x for x in ds if x != d)

jumlah_email = ham["sender_domain"].value_counts()
print("8 domain ham dengan 'tetangga' terbanyak:")
for d in sorted(tetangga, key=lambda x: -len(tetangga[x]))[:8]:
    print(f"  {d:28} tetangga={len(tetangga[d]):3}  email_ham={jumlah_email.get(d, 0)}")

ham_mask = df["label"].eq("ham").to_numpy()
n_ham = int(ham_mask.sum())
buang = []
print("\nlangkah | domain dibuang (derajat)        | grup ham terbesar | jumlah grup ham")
for langkah in range(11):
    g = grup_c(buang)
    ukuran = pd.Series(g[ham_mask]).value_counts()
    nama = f"{buang[-1]} ({len(tetangga[buang[-1]])})" if buang else "(belum ada)"
    print(f"{langkah:7} | {nama:31} | {ukuran.iloc[0]:4} ({ukuran.iloc[0] / n_ham * 100:4.1f}%)"
          f"      | {len(ukuran)}")
    if ukuran.iloc[0] / n_ham < TARGET:
        print("Target tercapai.")
        break
    besar = ukuran.index[0]
    kandidat = [d for d in df.loc[g == besar, "sender_domain"].unique()
                if d in tetangga and d not in buang]
    if not kandidat:
        print("Tidak ada kandidat jembatan lagi.")
        break
    buang.append(max(kandidat, key=lambda x: len(tetangga[x])))