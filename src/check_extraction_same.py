"""Buktikan ekstraksi ulang tidak mengubah kolom LAMA.

Membandingkan CSV interim (baru) dengan bagian yang sesuai di emails_all.csv
(dibuat dari ekstraksi lama). Hanya angka agregat.
Pakai: python -m src.check_extraction_same spamassassin   (atau: nazario)
"""
import sys
from email import message_from_string

import pandas as pd

from src.email_parser import ekstrak_metadata

PATH = {"spamassassin": "data/interim/spamassassin/spamassassin_clean.csv",
        "nazario": "data/interim/nazario/nazario_clean.csv"}
nama = sys.argv[1]
META = list(ekstrak_metadata(message_from_string("")).keys())
LAMA = ["source_file", "subject", "body_text", "n_urls", "urls_defanged",
        "n_attachments", "content_hash", "sender_domain"] + META
if nama == "spamassassin":
    LAMA += ["label", "subset"]

baru = pd.read_csv(PATH[nama], keep_default_na=False, dtype=str)
lama = pd.read_csv("data/processed/emails_all.csv", keep_default_na=False, dtype=str)
lama = lama[lama["source"] == nama].reset_index(drop=True)
print("Baris baru:", len(baru), "| baris lama:", len(lama))
assert len(baru) == len(lama), "jumlah baris berbeda"

beda = {c: int((baru[c] != lama[c]).sum()) for c in LAMA}
bermasalah = {c: n for c, n in beda.items() if n}
print("Kolom lama dibandingkan:", len(LAMA), "| kolom dengan perbedaan:", bermasalah or "TIDAK ADA")

# --- Cek wajar kolom BARU (agregat per subset) ---
kunci = "subset" if "subset" in baru.columns else "source_file"
NUM = ["n_urls", "n_links", "n_link_mismatch", "n_link_ip"]
x = baru.copy()
for c in NUM:
    x[c] = x[c].astype(float)
ring = x.groupby(kunci).agg(
    n=("n_links", "size"),
    persen_urls_lama=("n_urls", lambda s: round((s > 0).mean() * 100, 1)),
    persen_links_baru=("n_links", lambda s: round((s > 0).mean() * 100, 1)),
    links_median=("n_links", "median"),
    persen_mismatch=("n_link_mismatch", lambda s: round((s > 0).mean() * 100, 1)),
    persen_ip=("n_link_ip", lambda s: round((s > 0).mean() * 100, 1)),
    persen_header_names_kosong=("header_names", lambda s: round((s == "").mean() * 100, 1)),
)
print("\nRingkasan kolom baru per", kunci, ":")
print(ring.to_string())