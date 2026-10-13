"""Inspeksi agregat satu mbox remote. Jalankan HANYA di dalam container.

Mencetak angka saja: jumlah email, jumlah ber-lampiran, sebaran tipe konten.
Tidak mencetak isi, tidak men-decode lampiran, tidak merender HTML.
"""
import collections
import mailbox
import sys
import tempfile
import urllib.request

url = sys.argv[1]
with urllib.request.urlopen(url, timeout=120) as r:
    data = r.read()

with tempfile.NamedTemporaryFile(suffix=".mbox") as tmp:
    tmp.write(data)
    tmp.flush()
    box = mailbox.mbox(tmp.name)

    total = 0
    dengan_lampiran = 0
    tipe_utama = collections.Counter()
    for msg in box:
        total += 1
        tipe_utama[msg.get_content_type()] += 1
        punya_lampiran = False
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_filename():
                    punya_lampiran = True
                    break
        dengan_lampiran += punya_lampiran

print("Ukuran (byte):", len(data))
print("Jumlah email (parser):", total)
print("Email dengan lampiran:", dengan_lampiran)
print("Tipe konten utama:")
for tipe, n in tipe_utama.most_common(8):
    print(f"  {tipe}: {n}")