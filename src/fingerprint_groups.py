"""Sidik jari PARTISI grup di emails_clean.csv (tidak peka penomoran ulang group_id).

python src/fingerprint_groups.py simpan       -> rekam kondisi SEKARANG (hanya sekali)
python src/fingerprint_groups.py bandingkan   -> bandingkan dengan rekaman
Hanya hash dan angka; tanpa isi email.
"""
import hashlib
import json
import os
import sys

import pandas as pd

OUT = "data/processed/fingerprint_groups_before.json"

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "group_id"])
wakil = df.groupby("group_id")["content_hash"].transform("min")   # wakil grup = hash terkecil
pasangan = sorted(zip(df["content_hash"], wakil))
sekarang = {
    "baris": len(df),
    "n_grup": int(df["group_id"].nunique()),
    "sha_partisi": hashlib.sha256(
        "\n".join(f"{a}:{b}" for a, b in pasangan).encode()).hexdigest()[:16],
    "sha_urutan_baris": hashlib.sha256("\n".join(df["content_hash"]).encode()).hexdigest()[:16],
}

mode = sys.argv[1] if len(sys.argv) > 1 else "simpan"
if mode == "simpan":
    if os.path.exists(OUT):
        sys.exit(f"{OUT} sudah ada. Tidak ditimpa.")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(sekarang, f, indent=1)
    print(json.dumps(sekarang, indent=1))
elif mode == "bandingkan":
    with open(OUT, encoding="utf-8") as f:
        sebelum = json.load(f)
    for k, v in sekarang.items():
        print(f"{k:18} {'SAMA' if sebelum[k] == v else 'BEDA'}  sebelum={sebelum[k]}  sesudah={v}")
else:
    sys.exit("Mode: simpan atau bandingkan")