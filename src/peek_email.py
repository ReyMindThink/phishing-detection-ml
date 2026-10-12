"""Intip struktur satu email: hanya NAMA header, bukan isinya.

Aman: hanya membaca teks, tidak merender HTML, tidak membuka lampiran.
"""
import sys
from email import policy
from email.parser import BytesParser

path = sys.argv[1]
with open(path, "rb") as f:
    msg = BytesParser(policy=policy.compat32).parse(f)

print("Jumlah header:", len(msg.keys()))
print("Nama header:", msg.keys())
print("Multipart:", msg.is_multipart())
print("Content-Type:", msg.get_content_type())
print("Charset:", msg.get_content_charset())