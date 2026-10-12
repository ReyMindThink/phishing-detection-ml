"""Intip struktur MeAJOR: nama kolom, tipe, jumlah, dan sebaran kolom kategori.

Aman: tidak menampilkan isi teks email. Kolom dengan banyak nilai unik
(misalnya teks email) hanya dilaporkan jumlah unik dan rata-rata panjangnya.
"""
import pandas as pd

PATH = "data/raw/meajor_cleaned_preprocessed.parquet.gzip"
MAX_UNIK_UNTUK_DITAMPILKAN = 20

df = pd.read_parquet(PATH)

print("Shape (baris, kolom):", df.shape)
print()
print("=== Kolom, tipe, nilai kosong, jumlah nilai unik ===")
for col in df.columns:
    print(f"{col!r:45} {str(df[col].dtype):12} kosong={df[col].isna().sum():<8} unik={df[col].nunique(dropna=True)}")

print()
print("=== Sebaran kolom kategori (maks 20 nilai unik) ===")
for col in df.columns:
    n_unik = df[col].nunique(dropna=True)
    if n_unik <= MAX_UNIK_UNTUK_DITAMPILKAN:
        print(f"\n[{col}]")
        print(df[col].value_counts(dropna=False).to_string())

print()
print("=== Kolom teks: rata-rata panjang karakter (tanpa menampilkan isi) ===")
for col in df.columns:
    if pd.api.types.is_string_dtype(df[col]):
        panjang = df[col].dropna().astype(str).str.len()
        if len(panjang) > 0:
            print(f"{col!r:45} rata-rata={panjang.mean():.0f} median={panjang.median():.0f} maks={panjang.max()}")