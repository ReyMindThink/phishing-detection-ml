"""Gabungkan SpamAssassin + Nazario menjadi satu tabel seragam.

Termasuk kolom metadata bentuk email. Hanya mencetak angka agregat.
"""
from email import message_from_string

import pandas as pd

from src.email_parser import ekstrak_metadata, fitur_link

SA = "data/interim/spamassassin/spamassassin_clean.csv"
NZ = "data/interim/nazario/nazario_clean.csv"
OUT = "data/processed/emails_all.csv"
META = list(ekstrak_metadata(message_from_string("")).keys())
LINK = list(fitur_link(message_from_string("")).keys())

sa = pd.read_csv(SA, keep_default_na=False)
nz = pd.read_csv(NZ, keep_default_na=False)

sa["source"] = "spamassassin"
nz["label"] = "phishing"
nz["subset"] = nz["source_file"]
nz["source"] = "nazario"

kolom = ["source", "subset", "source_file", "label", "subject", "body_text",
         "n_urls", "urls_defanged", "n_attachments", "content_hash",
         "sender_domain"] + META + LINK + ["header_names"]
df = pd.concat([sa[kolom], nz[kolom]], ignore_index=True)
df.to_csv(OUT, index=False)

print("Shape:", df.shape)
print("\nLabel x sumber:")
print(pd.crosstab(df["label"], df["source"], margins=True).to_string())