"""Model beku: muat dengan verifikasi SHA256 SEBELUM joblib.load (berkas joblib/pickle bisa
menjalankan kode saat dimuat, jadi hanya berkas yang hash-nya cocok dengan manifest yang dimuat)."""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np

URUTAN = ["ham", "spam", "phishing"]
MANIFEST = "docs/model_manifest.json"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def muat_terverifikasi(path, sha_diharapkan):
    """Hitung SHA256 dulu; hanya bila cocok baru dimuat."""
    if sha256_file(path) != sha_diharapkan:
        raise ValueError("SHA256 tidak cocok untuk %s: model TIDAK dimuat" % path)
    return joblib.load(path)


def proba_ensemble(models, teks):
    """Rata-rata proba (ham, spam, phishing) dari semua model; kolom diurutkan sesuai URUTAN."""
    hasil = []
    for m in models:
        urut = [list(m.classes_).index(c) for c in URUTAN]
        hasil.append(m.predict_proba(teks)[:, urut])
    return np.mean(hasil, axis=0)


def putusan(proba, ambang):
    """phishing bila P(phishing) >= ambang; selain itu ham/spam mana yang lebih besar (seri: ham)."""
    lain = np.where(proba[:, 0] >= proba[:, 1], "ham", "spam")
    return np.where(proba[:, 2] >= ambang, "phishing", lain)


def muat_ensemble(path_manifest=MANIFEST):
    manifest = json.loads(Path(path_manifest).read_text(encoding="utf-8"))
    models = [muat_terverifikasi(m["path"], m["sha256"]) for m in manifest["models"]]
    return models, manifest