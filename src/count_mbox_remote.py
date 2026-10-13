"""Hitung jumlah email dalam satu mbox remote, seluruhnya di memori.

Tidak menulis file ke disk, tidak mengekstrak lampiran, tidak merender HTML.
Hanya mencetak angka agregat.
"""
import sys
import urllib.request

url = sys.argv[1]
with urllib.request.urlopen(url, timeout=120) as r:
    data = r.read()

print("Ukuran (byte):", len(data))
# Dalam format mbox, setiap email diawali baris yang dimulai dengan "From ".
jumlah = data.count(b"\nFrom ") + (1 if data.startswith(b"From ") else 0)
print("Perkiraan jumlah email:", jumlah)