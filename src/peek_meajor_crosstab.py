"""Tabel silang sumber x label, dan sebaran tahun. Hanya angka agregat."""
import pandas as pd

PATH = "data/raw/meajor_cleaned_preprocessed.parquet.gzip"
df = pd.read_parquet(PATH, columns=["source", "label", "date", "language"])

print("=== Sumber x label (jumlah baris) ===")
print(pd.crosstab(df["source"], df["label"], margins=True, dropna=False).to_string())

print()
print("=== Persen tiap label per sumber ===")
print((pd.crosstab(df["source"], df["label"], normalize="index") * 100).round(1).to_string())

tahun = pd.to_datetime(df["date"], errors="coerce", utc=True, format="mixed").dt.year
print()
print("=== Tahun x sumber ===")
print(pd.crosstab(tahun, df["source"]).to_string())
print("Tanggal gagal dibaca:", int(tahun.isna().sum()))

print()
print("=== 5 bahasa terbanyak ===")
print(df["language"].value_counts().head(5).to_string())