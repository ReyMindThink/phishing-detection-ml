"""Uji konsistensi lintas versi Python: sidik jari keluaran parser per email.

Hanya hash (tanpa isi email). Jalankan lokal dan di Docker, lalu bandingkan.
Pakai: python -m src.env_digest <berkas_keluaran.csv>
"""
import csv
import hashlib
import re
import sys
from email import message_from_binary_file
from pathlib import Path

from src.email_parser import (domain_pengirim, ekstrak_metadata, fitur_link,
                              nama_header, parse_pesan)

ROOT = Path("data/interim/spamassassin")
POLA = re.compile(r"^[0-9]{5}\.[0-9a-f]{32}$")
SUBSETS = ["easy_ham", "easy_ham_2", "hard_ham", "spam", "spam_2"]


def d(x):
    return hashlib.sha256(repr(x).encode("utf-8", "replace")).hexdigest()[:12]


n_ok = n_gagal = 0
with open(sys.argv[1], "w", newline="", encoding="utf-8") as out:
    w = csv.writer(out)
    w.writerow(["source_file", "teks", "meta", "link", "header_names", "domain"])
    for s in SUBSETS:
        for p in sorted((ROOT / s).iterdir()):
            if not POLA.match(p.name):
                continue
            try:
                with open(p, "rb") as f:
                    msg = message_from_binary_file(f)
                baris = [f"{s}/{p.name}", d(parse_pesan(msg)), d(ekstrak_metadata(msg)),
                         d(fitur_link(msg)), d(nama_header(msg)), d(domain_pengirim(msg))]
                n_ok += 1
            except Exception:
                baris = [f"{s}/{p.name}", "ERR", "ERR", "ERR", "ERR", "ERR"]
                n_gagal += 1
            w.writerow(baris)

print("Python", sys.version.split()[0], "| berhasil:", n_ok, "| gagal:", n_gagal)