"""Pada email dengan teks persis sama (content_hash sama), seberapa sering fitur link
berbeda antar salinan? Hanya angka agregat."""
import pandas as pd

KOLOM = ["n_links", "n_link_domains", "domains_link_defanged",
         "n_link_mismatch", "n_images", "n_forms"]
df = pd.read_csv("data/processed/emails_all.csv", keep_default_na=False,
                 usecols=["label", "content_hash"] + KOLOM)
ukuran = df.groupby("content_hash")["label"].transform("size")
dup = df[ukuran > 1]
print("Email dalam kelompok duplikat exact:", len(dup), "dari", len(df),
      "| jumlah kelompok:", dup["content_hash"].nunique())

print("\n% kelompok duplikat yang fiturnya BEDA antar salinan:")
for label in ["ham", "spam", "phishing"]:
    g = dup[dup["label"] == label].groupby("content_hash")
    if g.ngroups == 0:
        print(f"{label:9} tidak ada kelompok duplikat")
        continue
    baris = [f"{label:9} kelompok={g.ngroups:5}"]
    for c in KOLOM:
        baris.append(f"{c}: {(g[c].nunique() > 1).sum() / g.ngroups * 100:4.1f}%")
    print(" | ".join(baris))