"""Ekspor daftar split tanpa isi email: docs/split_list.tsv.

Kolom: content_hash, label, group_final, split, fold (dipisah tab, akhir baris LF, urut menurut content_hash).
Sumber kebenaran: data/processed/splits.csv. emails_clean.csv hanya dipakai untuk kontrol.
Hanya hash, label, nomor grup, dan bagian; tanpa isi email. Tidak menimpa berkas yang sudah ada.
Jalankan: python -m src.export_split_list
"""
import hashlib
import os
import re
from pathlib import Path

import pandas as pd

KONTROL = os.environ.get("UJI_ALUR_SINTETIS") != "1"    # "1" HANYA untuk menguji alur pada data sintetis
SPLITS = "data/processed/splits.csv"
CLEAN = "data/processed/emails_clean.csv"
OUT = Path("docs/split_list.tsv")
KOLOM = ["content_hash", "label", "group_final", "split", "fold"]
if OUT.exists():
    raise SystemExit(f"{OUT} sudah ada. Tidak ditimpa.")

sp = pd.read_csv(SPLITS, keep_default_na=False)
cl = pd.read_csv(CLEAN, keep_default_na=False, usecols=["content_hash", "group_id"])
assert list(sp.columns) == KOLOM, "kolom splits.csv tidak sesuai"
assert sp["content_hash"].is_unique and set(sp["content_hash"]) == set(cl["content_hash"]), "hash splits.csv beda dari emails_clean.csv"
assert sp["content_hash"].map(lambda h: re.fullmatch(r"[0-9a-f]{64}", h) is not None).all(), "content_hash bukan SHA256 heksadesimal"

# Kontrol 1: sidik jari partisi group_id (rumus sama dengan src/fingerprint_groups.py)
wakil = cl.groupby("group_id")["content_hash"].transform("min")
sha = hashlib.sha256("\n".join(f"{a}:{b}" for a, b in sorted(zip(cl["content_hash"], wakil))).encode()).hexdigest()[:16]

# Kontrol 2: tidak ada grup yang terbelah (aturan yang sama dengan make_splits.py)
assert (sp.groupby("group_final")["split"].nunique() == 1).all(), "grup terbelah train/test"
tr, te = sp[sp["split"] == "train"], sp[sp["split"] == "test"]
assert (tr.groupby("group_final")["fold"].nunique() == 1).all(), "grup terbelah antar-fold"
assert set(tr["fold"]) == {0, 1, 2, 3, 4} and set(te["fold"]) == {-1}, "nilai fold tidak sesuai"
assert set(sp["split"]) == {"train", "test"}

# Kontrol 3: angka yang tercatat (lewati hanya untuk uji alur sintetis)
if KONTROL:
    assert len(sp) == 9298 and len(cl) == 9298, "jumlah baris"
    assert sp["group_final"].nunique() == 4741, "jumlah group_final"
    assert sha == "a0edd8587f0fcc56", f"sidik jari partisi berbeda: {sha}"
    jumlah = sp.groupby(["split", "label"]).size().to_dict()
    assert jumlah == {("train", "ham"): 3288, ("train", "spam"): 1448, ("train", "phishing"): 2702,
                      ("test", "ham"): 822, ("test", "spam"): 362, ("test", "phishing"): 676}, jumlah

urut = sp.sort_values("content_hash").reset_index(drop=True)
urut.to_csv(OUT, sep="\t", index=False, lineterminator="\n")
kembali = pd.read_csv(OUT, sep="\t", keep_default_na=False)
assert kembali.equals(urut), "isi berkas tidak sama dengan data sumber setelah dibaca ulang"
print("KONTROL OK:", len(urut), "baris;", urut["group_final"].nunique(), "grup; sha_partisi", sha)
print(urut.groupby(["split", "label"]).size().to_string())
print("Tersimpan:", OUT, "|", OUT.stat().st_size, "byte")