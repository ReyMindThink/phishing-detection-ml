"""Ekstrak Nazario MODERN (phishing-2015 s.d. phishing-2025) ke CSV bersih. HANYA DI DALAM CONTAINER.

Salinan extract_nazario.py (parser sama) dengan daftar file modern. SEBELUM mengunduh apa pun, semua file
dicek dengan permintaan HEAD (status 200, ukuran terbaca dan < 40 MB); bila ada yang gagal, berhenti.
Lampiran tidak di-decode. Hanya CSV teks bersih yang keluar ke /out. Utang teknis: gabungkan di Tahap 13.
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
FILES = ["phishing-%d" % y for y in range(2015, 2026)]
BATAS_BYTE = 40_000_000
KOLOM_META = list(ekstrak_metadata(message_from_string("")).keys())
KOLOM_LINK = list(fitur_link(message_from_string("")).keys())
KOLOM = ["source_file", "subject", "body_text", "n_urls",
         "urls_defanged", "n_attachments", "content_hash", "sender_domain"] + KOLOM_META + KOLOM_LINK + ["header_names"]

ringkasan = {}
for nama in FILES:
    req = urllib.request.Request(BASE + nama, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        status, panjang = r.status, r.headers.get("Content-Length")
    print(f"cek {nama}: HTTP {status}, Content-Length={panjang}", flush=True)
    assert status == 200 and panjang is not None and int(panjang) < BATAS_BYTE, nama
with open("/out/nazario_modern_clean.csv", "w", newline="", encoding="utf-8") as out:
    w = csv.DictWriter(out, fieldnames=KOLOM)
    w.writeheader()
    for nama in FILES:
        with urllib.request.urlopen(BASE + nama, timeout=180) as r:
            data = r.read()
        n_ok, n_gagal, n_kosong = 0, 0, 0
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
                n_kosong += h["body_text"].strip() == ""
        ringkasan[nama] = (n_ok, n_gagal, n_kosong)

for nama, (ok, gagal, kosong) in ringkasan.items():
    print(f"{nama}: berhasil={ok} gagal={gagal} body_kosong={kosong}")