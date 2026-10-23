"""Sidik jari data: jumlah baris + ringkasan hash content_hash. Tanpa isi email.

python src/fingerprint_data.py simpan       -> simpan kondisi SEKARANG (hanya sekali)
python src/fingerprint_data.py bandingkan   -> bandingkan kondisi sekarang dengan yang disimpan
"""
import hashlib
import json
import os
import sys

import pandas as pd

OUT = "data/processed/fingerprint_before.json"
SPLITS = "data/processed/splits.csv"
BERKAS = {
    "spamassassin_clean": "data/interim/spamassassin/spamassassin_clean.csv",
    "nazario_clean": "data/interim/nazario/nazario_clean.csv",
    "emails_all": "data/processed/emails_all.csv",
    "emails_clean": "data/processed/emails_clean.csv",
}


def sha_daftar(seri):
    return hashlib.sha256("\n".join(sorted(seri)).encode("utf-8")).hexdigest()[:16]


def ukur():
    hasil = {}
    for nama, path in BERKAS.items():
        h = pd.read_csv(path, keep_default_na=False, usecols=["content_hash"])["content_hash"]
        hasil[nama] = {"baris": len(h), "unik": int(h.nunique()), "sha_hash": sha_daftar(h)}
    sp = pd.read_csv(SPLITS, keep_default_na=False)
    hasil["splits"] = {"baris": len(sp), "unik": int(sp["content_hash"].nunique()),
                       "sha_hash": sha_daftar(sp["content_hash"])}
    with open(SPLITS, "rb") as f:
        hasil["splits_sha_berkas"] = hashlib.sha256(f.read()).hexdigest()[:16]
    hasil["kolom_emails_clean"] = list(pd.read_csv(BERKAS["emails_clean"], nrows=0).columns)
    return hasil


mode = sys.argv[1] if len(sys.argv) > 1 else "simpan"
sekarang = ukur()

if mode == "simpan":
    if os.path.exists(OUT):
        sys.exit(f"{OUT} sudah ada. Tidak ditimpa. Hapus manual hanya bila benar-benar ingin mengulang.")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(sekarang, f, indent=1)
    ringkas = {k: v for k, v in sekarang.items() if k != "kolom_emails_clean"}
    print(json.dumps(ringkas, indent=1))
    print("Jumlah kolom emails_clean:", len(sekarang["kolom_emails_clean"]))
    print("Hash di splits.csv == hash di emails_clean.csv:",
          sekarang["splits"]["sha_hash"] == sekarang["emails_clean"]["sha_hash"])
    print("Tersimpan:", OUT)
elif mode == "bandingkan":
    with open(OUT, encoding="utf-8") as f:
        sebelum = json.load(f)
    for nama in list(BERKAS) + ["splits"]:
        a, b = sebelum[nama], sekarang[nama]
        sama = (a["baris"], a["unik"], a["sha_hash"]) == (b["baris"], b["unik"], b["sha_hash"])
        print(f"{nama:20} {'SAMA' if sama else 'BEDA'}  "
              f"sebelum={a['baris']}/{a['unik']}  sesudah={b['baris']}/{b['unik']}")
    print("splits.csv (isi berkas):",
          "SAMA" if sebelum["splits_sha_berkas"] == sekarang["splits_sha_berkas"] else "BEDA")
    baru = [c for c in sekarang["kolom_emails_clean"] if c not in sebelum["kolom_emails_clean"]]
    print("Kolom baru di emails_clean:", len(baru), baru)
else:
    sys.exit("Mode: simpan atau bandingkan")