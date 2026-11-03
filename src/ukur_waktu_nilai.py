"""Tahap 11-2: ukur waktu penilaian pada teks sebesar batas (100.000 karakter) dengan model asli. Hanya angka waktu."""
import json
import time
from pathlib import Path

from src.app import BATAS_TEKS, SAMPLES, buat_app
from src.penilai import muat_penilai

ULANG = 3


def isi(unit, n=BATAS_TEKS):
    return (unit * (n // len(unit) + 1))[:n]


def kasus(pen, e09):
    return {
        "E09 diulang": isi(e09 + " "),
        "kosakata penuh": isi(" ".join(sorted(pen.kenal)) + " "),
        "kata pendek abc": isi("abc "),
        "satu token panjang": "a" * BATAS_TEKS,
        "spasi saja": " " * BATAS_TEKS,
        "http beruntun": isi("http://"),
        "hxxp bersela": isi("hxxp://x "),
    }


def main():
    pen = muat_penilai()
    contoh = json.loads(Path(SAMPLES).read_text(encoding="utf-8"))
    e09 = next(c["teks"] for c in contoh if c["id"] == "E09")
    k = buat_app(penilai=pen).test_client()
    k.post("/analyze", json={"teks": e09})
    for nama, teks in kasus(pen, e09).items():
        assert len(teks) == BATAS_TEKS, (nama, len(teks))
        t = []
        for _ in range(ULANG):
            a = time.perf_counter()
            r = k.post("/analyze", json={"teks": teks})
            t.append(time.perf_counter() - a)
            assert r.status_code == 200, (nama, r.status_code)
        print(f"{nama}: status 200 min={min(t):.3f}s maks={max(t):.3f}s")


if __name__ == "__main__":
    main()