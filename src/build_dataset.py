"""Gabungkan SpamAssassin + Nazario menjadi satu tabel seragam.

Hanya mencetak angka agregat. Tidak menampilkan isi email.
"""
import pandas as pd

SA = "data/interim/spamassassin/spamassassin_clean.csv"
NZ = "data/interim/nazario/nazario_clean.csv"
OUT = "data/processed/emails_all.csv"

sa = pd.read_csv(SA, keep_default_na=False)
nz = pd.read_csv(NZ, keep_default_na=False)

sa["source"] = "spamassassin"
nz["label"] = "phishing"
nz["subset"] = nz["source_file"]
nz["source"] = "nazario"

kolom = ["source", "subset", "source_file", "label", "subject", "body_text",
         "n_urls", "urls_defanged", "n_attachments", "content_hash"]
df = pd.concat([sa[kolom], nz[kolom]], ignore_index=True)
df.to_csv(OUT, index=False)

print("Shape:", df.shape)
print("\nLabel x sumber:")
print(pd.crosstab(df["label"], df["source"], margins=True).to_string())
print("\nRingkasan per label:")
df["panjang_body"] = df["body_text"].str.len()
ringkas = df.groupby("label").agg(
    n=("label", "size"),
    median_panjang=("panjang_body", "median"),
    rata_url=("n_urls", "mean"),
    persen_tanpa_url=("n_urls", lambda s: round((s == 0).mean() * 100, 1)),
    persen_lampiran=("n_attachments", lambda s: round((s > 0).mean() * 100, 1)),
    persen_body_kosong=("panjang_body", lambda s: round((s == 0).mean() * 100, 1)),
)
print(ringkas.round(1).to_string())