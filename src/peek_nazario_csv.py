"""Ringkasan agregat nazario_clean.csv. Tidak menampilkan isi teks."""
import pandas as pd

df = pd.read_csv("data/interim/nazario/nazario_clean.csv", keep_default_na=False)

print("Shape:", df.shape)
print("\nBaris per file:")
print(df["source_file"].value_counts().to_string())
print("\nHash unik:", df["content_hash"].nunique(), "dari", len(df))
print("Duplikat (hash sama):", len(df) - df["content_hash"].nunique())

panjang = df["body_text"].str.len()
print("\nPanjang body_text: median=%d rata-rata=%d maks=%d" % (panjang.median(), panjang.mean(), panjang.max()))
print("Body kosong:", int((panjang == 0).sum()))
print("Subject kosong:", int((df["subject"] == "").sum()))
print("\nn_urls: median=%d maks=%d, email tanpa URL: %d" % (df["n_urls"].median(), df["n_urls"].max(), int((df["n_urls"] == 0).sum())))
print("Email ber-lampiran:", int((df["n_attachments"] > 0).sum()))

print("\nDuplikat per kombinasi file (hash yang muncul di >1 file):")
per_hash = df.groupby("content_hash")["source_file"].nunique()
print("Hash yang muncul di lebih dari satu file:", int((per_hash > 1).sum()))