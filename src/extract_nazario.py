"""Ekstrak Nazario ke CSV bersih. JALANKAN HANYA DI DALAM CONTAINER.

Mengunduh mbox ke memori, menulis berkas sementara di dalam container saja,
dan hanya mengeluarkan teks bersih + angka ke /out. Lampiran tidak di-decode.
Termasuk metadata bentuk email (ekstrak_metadata), sama dengan SpamAssassin.
"""
import csv
import hashlib
import mailbox
import sys
import tempfile
import urllib.request
from email import message_from_string

sys.path.insert(0, "/app")
from src.email_parser import domain_pengirim, ekstrak_metadata, fitur_link, nama_header, parse_pesan  # noqa: E402

BASE = "https://monkey.org/~jose/phishing/"
FILES = ["phishing0.mbox", "phishing1.mbox", "phishing2.mbox",
         "phishing3.mbox", "20051114.mbox"]
KOLOM_META = list(ekstrak_metadata(message_from_string("")).keys())
KOLOM_LINK = list(fitur_link(message_from_string("")).keys())
KOLOM = ["source_file", "subject", "body_text", "n_urls",
         "urls_defanged", "n_attachments", "content_hash", "sender_domain"] + KOLOM_META + KOLOM_LINK + ["header_names"]

ringkasan = {}
with open("/out/nazario_clean.csv", "w", newline="", encoding="utf-8") as out:
    w = csv.DictWriter(out, fieldnames=KOLOM)
    w.writeheader()
    for nama in FILES:
        with urllib.request.urlopen(BASE + nama, timeout=180) as r:
            data = r.read()
        n_ok, n_gagal = 0, 0
        with tempfile.NamedTemporaryFile(suffix=".mbox") as tmp:
            tmp.write(data)
            tmp.flush()
            for msg in mailbox.mbox(tmp.name):
                try:
                    h = parse_pesan(msg)
                    m = ekstrak_metadata(msg)
                    dom = domain_pengirim(msg)
                    lk = fitur_link(msg)
                    hn = nama_header(msg)
                except Exception:
                    n_gagal += 1
                    continue
                kunci = (h["subject"] + "\n" + h["body_text"]).encode("utf-8", "replace")
                w.writerow({
                    "source_file": nama,
                    "subject": h["subject"],
                    "body_text": h["body_text"],
                    "n_urls": h["n_urls"],
                    "urls_defanged": " ".join(h["urls_defanged"]),
                    "n_attachments": h["n_attachments"],
                    "content_hash": hashlib.sha256(kunci).hexdigest(),
                    "sender_domain": dom,
                    **m,
                    **lk,
                    "header_names": hn,
                })
                n_ok += 1
        ringkasan[nama] = (n_ok, n_gagal)

for nama, (ok, gagal) in ringkasan.items():
    print(f"{nama}: berhasil={ok} gagal={gagal}")