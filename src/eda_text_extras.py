"""Tahap 5d-6: EDA ringan penutup 5d (subjek, kata urgensi daftar tulis tangan,
statistik teks). Hanya TRAIN. Hanya angka agregat; isi subjek TIDAK dicetak."""
import re

import pandas as pd

ANCAMAN = re.compile(r"\b(?:urgent|immediately|suspend(?:ed)?|expire[sd]?|locked|"
                     r"unauthori[sz]ed|terminat(?:ed|ion)|deactivat(?:ed|ion)|"
                     r"restricted|warning|alert)\b")
AKSI = re.compile(r"\b(?:verify|confirm|validate|login|log in|sign in|password)\b")
RE_SUBJ = re.compile(r"re\s*:", re.IGNORECASE)
URUTAN = ["ham", "spam", "phishing"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "has_html", "subject", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
df["has_html"] = df["has_html"].astype(str) == "True"

s = df["subject"].str.strip()
df["kosong"] = s == ""
df["kurung"] = s.str.startswith("[")
df["re"] = s.str.match(RE_SUBJ)
t = df["body_text"].str.lower()
df["ancaman"] = t.str.contains(ANCAMAN)
df["aksi"] = t.str.contains(AKSI)
df["panjang"] = df["body_text"].str.len()


def rasio_besar(x):
    huruf = [c for c in x if c.isalpha()]
    return sum(c.isupper() for c in huruf) / len(huruf) if huruf else 0.0


def rasio_angka(x):
    return sum(c.isdigit() for c in x) / len(x) if x else 0.0


df["r_besar"] = df["body_text"].map(rasio_besar)
df["r_angka"] = df["body_text"].map(rasio_angka)


def tabel(d, kunci):
    baris = {}
    for k, g in d.groupby(kunci):
        baris[k] = {"n": len(g),
                    "%kosong": g["kosong"].mean() * 100,
                    "%[": g["kurung"].mean() * 100,
                    "%Re:": g["re"].mean() * 100,
                    "%ancaman": g["ancaman"].mean() * 100,
                    "%aksi": g["aksi"].mean() * 100,
                    "med_pjg": g["panjang"].median(),
                    "med_%bsr": g["r_besar"].median() * 100,
                    "med_%angka": g["r_angka"].median() * 100}
    out = pd.DataFrame(baris).T
    out["n"] = out["n"].astype(int)
    out["catatan"] = ["n<30 *" if n < 30 else "" for n in out["n"]]
    return out.round(1)


html = df[df["has_html"]]
print("Train:", len(df), "| HTML:", len(html))
print("\n=== Semua train, per KELAS ===")
print(tabel(df, "label").loc[URUTAN].to_string())
print("\n=== Email HTML saja, per KELAS ===")
print(tabel(html, "label").loc[URUTAN].to_string())
print("\n=== Semua train, per SUBSET ===")
print(tabel(df, "subset").to_string())
print("\n=== Email HTML saja, per SUBSET ===")
print(tabel(html, "subset").to_string())