"""Duplikat exact (hash teks bersih) per label, per sumber, dan lintas label.

Hanya angka agregat. Tidak menampilkan isi email.
"""
import pandas as pd

df = pd.read_csv("data/processed/emails_all.csv", keep_default_na=False)

print("=== Per label: total, unik, duplikat ===")
for label, g in df.groupby("label"):
    n, u = len(g), g["content_hash"].nunique()
    print(f"{label:9} total={n:5} unik={u:5} duplikat={n-u:5} ({(n-u)/n*100:.1f}%)")

print("\n=== Hash yang muncul di lebih dari satu label (konflik label) ===")
per_hash = df.groupby("content_hash")["label"].nunique()
konflik = per_hash[per_hash > 1].index
print("Jumlah hash konflik:", len(konflik))
if len(konflik):
    print(pd.crosstab(df[df["content_hash"].isin(konflik)]["label"],
                      df[df["content_hash"].isin(konflik)]["source"]).to_string())

print("\n=== Duplikat antar subset dalam SpamAssassin ===")
sa = df[df["source"] == "spamassassin"]
per_hash_sub = sa.groupby("content_hash")["subset"].nunique()
print("Hash di >1 subset:", int((per_hash_sub > 1).sum()))

print("\n=== Hash kosong (subject dan body sama-sama kosong) ===")
kosong = df[(df["subject"] == "") & (df["body_text"] == "")]
print(kosong["label"].value_counts().to_string() if len(kosong) else "tidak ada")