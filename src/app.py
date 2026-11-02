"""Tahap 10b: API Flask untuk penilai. Model dimuat saat startup lewat muat_penilai (SHA256 diperiksa); bila hash
tidak cocok, buat_app melempar ValueError dan aplikasi TIDAK jalan. Teks masukan tidak disimpan, tidak dicatat, dan tidak
dikembalikan. Server hanya untuk 127.0.0.1 dengan debug mati. Jalankan: python -m src.app"""
import json
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from src.frozen_model import MANIFEST
from src.penilai import ATURAN, muat_penilai

SAMPLES = "samples/contoh_fiktif.json"
CATATAN = ("Skor adalah skor model, BUKAN probabilitas. TIDAK DAPAT DINILAI berarti periksa manual; tidak ada dasar "
           "untuk menyatakan email itu bersih. Model dilatih pada email berbahasa Inggris 2002-2007 dan bukan alat keamanan utama.")


def buat_app(penilai=None, samples_path=SAMPLES, path_manifest=MANIFEST, path_aturan=ATURAN):
    pen = penilai if penilai is not None else muat_penilai(path_manifest, path_aturan)
    contoh = json.loads(Path(samples_path).read_text(encoding="utf-8"))
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(layanan="hidup", n_model=len(pen.models))

    @app.get("/samples")
    def samples():
        return jsonify(contoh)

    @app.get("/")
    def beranda():
        return app.send_static_file("index.html")

    @app.post("/analyze")
    def analyze():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get("teks"), str):
            return jsonify(error='Kirim JSON {"teks": "..."} dengan teks berupa string.'), 400
        hasil = pen.nilai(data["teks"])
        hasil["catatan"] = CATATAN
        return jsonify(hasil)

    @app.errorhandler(HTTPException)
    def galat(e):
        return jsonify(error=e.name), e.code

    return app


def main():
    buat_app().run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()