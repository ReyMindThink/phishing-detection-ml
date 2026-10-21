"""Ekstrak SpamAssassin ke CSV bersih dengan parser yang sama seperti Nazario.

Sekarang termasuk metadata bentuk email (ekstrak_metadata).
"""
import csv
import hashlib
import re
from email import message_from_binary_file, message_from_string
from pathlib import Path

from src.email_parser import domain_pengirim, ekstrak_metadata, parse_pesan

ROOT = Path("data/interim/spamassassin")
POLA = re.compile(r"^[0-9]{5}\.[0-9a-f]{32}$")
LABEL = {"easy_ham": "ham", "easy_ham_2": "ham", "hard_ham": "ham",
         "spam": "spam", "spam_2": "spam"}
KOLOM_META = list(ekstrak_metadata(message_from_string("")).keys())
KOLOM = ["source_file", "subject", "body_text", "n_urls",
         "urls_defanged", "n_attachments", "content_hash",
         "label", "subset", "sender_domain"] + KOLOM_META

ringkasan = {}
OUT = ROOT / "spamassassin_clean.csv"
with open(OUT, "w", newline="", encoding="utf-8") as out:
    w = csv.DictWriter(out, fieldnames=KOLOM)
    w.writeheader()
    for subset, label in LABEL.items():
        n_ok = n_gagal = 0
        for p in sorted((ROOT / subset).iterdir()):
            if not POLA.match(p.name):
                continue
            try:
                with open(p, "rb") as f:
                    msg = message_from_binary_file(f)
                h = parse_pesan(msg)
                m = ekstrak_metadata(msg)
                dom = domain_pengirim(msg)
            except Exception:
                n_gagal += 1
                continue
            kunci = (h["subject"] + "\n" + h["body_text"]).encode("utf-8", "replace")
            w.writerow({
                "source_file": f"{subset}/{p.name}",
                "subject": h["subject"],
                "body_text": h["body_text"],
                "n_urls": h["n_urls"],
                "urls_defanged": " ".join(h["urls_defanged"]),
                "n_attachments": h["n_attachments"],
                "content_hash": hashlib.sha256(kunci).hexdigest(),
                "label": label,
                "subset": subset,
                "sender_domain": dom,
                **m,
            })
            n_ok += 1
        ringkasan[subset] = (n_ok, n_gagal)

for subset, (ok, gagal) in ringkasan.items():
    print(f"{subset}: berhasil={ok} gagal={gagal}")