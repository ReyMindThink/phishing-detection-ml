"""Tahap 8-3-1: diagnosis FORMAT teks MeAJOR (hanya agregat, tidak mencetak isi email).

Pertanyaan: apakah body sudah teks biasa (tanpa tag HTML) dan token anonim apa yang ada?
Aturan membaca hasil dikunci di docs/experiment_design.md SEBELUM skrip ini dijalankan.
Jalankan: python src/meajor_diagnose.py
"""
import re
import sys

import pandas as pd

PATH = sys.argv[1] if len(sys.argv) > 1 else "data/raw/meajor_cleaned_preprocessed.parquet.gzip"
TOKEN_RE = re.compile(r"\[[A-Z][A-Z0-9_]{1,30}\]")
TAG_RE = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]{0,200})?/?>")
HTTP_RE = re.compile(r"https?://", re.IGNORECASE)

df = pd.read_parquet(PATH, columns=["body", "label", "source"])
n_awal = len(df)
df = df.dropna(subset=["body", "label"]).reset_index(drop=True)
df["label"] = df["label"].astype(int)
print("Baris awal %d | dibuang (body/label kosong): %d | dipakai: %d" % (n_awal, n_awal - len(df), len(df)))

body = df["body"]
tanda = pd.DataFrame({
    "token_anonim": body.str.contains(TOKEN_RE),
    "tag_html": body.str.contains(TAG_RE),
    "http_mentah": body.str.contains(HTTP_RE),
    "pendek_lt20": body.str.len() < 20,
})
print("\nPersen baris yang memuat pola, n per label:", df["label"].value_counts().sort_index().to_dict())
ringkas = tanda.groupby(df["label"]).mean() * 100
ringkas.loc["semua"] = tanda.mean() * 100
print(ringkas.round(1).to_string())

print("\nPersen per sumber (token_anonim, tag_html):")
print((tanda[["token_anonim", "tag_html"]].groupby(df["source"]).mean() * 100).round(1).to_string())

baris_token = body.str.findall(TOKEN_RE).map(set).explode().dropna().value_counts()
print("\nNama token anonim (jumlah BARIS yang memuatnya; hanya >= 50 baris, maks 12):")
print(baris_token[baris_token >= 50].head(12).to_string())

print("\nPanjang body (karakter), median dan persentil 90 per label:")
print(body.str.len().groupby(df["label"]).quantile([0.5, 0.9]).unstack().round(0).to_string())