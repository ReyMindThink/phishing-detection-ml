import hashlib
import tempfile
from pathlib import Path
from unittest import mock

import joblib
import numpy as np

from src.frozen_model import muat_terverifikasi, proba_ensemble, putusan, sha256_file


class Palsu:
    """Model palsu; urutan kelas sengaja bisa dibalik untuk menguji pengurutan kolom."""

    def __init__(self, kelas, proba):
        self.classes_ = np.array(kelas)
        self._p = np.array(proba, dtype=float)

    def predict_proba(self, teks):
        return self._p


def test_sha256_file_sama_dengan_hashlib():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.bin"
        p.write_bytes(b"abc" * 1000)
        assert sha256_file(p) == hashlib.sha256(b"abc" * 1000).hexdigest()


def test_muat_terverifikasi_cocok_memuat():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "m.joblib"
        joblib.dump({"a": 1}, p)
        assert muat_terverifikasi(p, sha256_file(p)) == {"a": 1}


def test_muat_terverifikasi_diubah_ditolak_sebelum_dimuat():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "m.joblib"
        joblib.dump({"a": 1}, p)
        sha_asli = sha256_file(p)
        p.write_bytes(p.read_bytes() + b"x")            # simulasi berkas diubah pihak lain
        with mock.patch("src.frozen_model.joblib.load", side_effect=AssertionError("dimuat!")):
            try:
                muat_terverifikasi(p, sha_asli)
            except ValueError:
                return
        assert False, "berkas yang diubah seharusnya ditolak"


def test_proba_ensemble_rata_rata_dan_urutan_kolom():
    a = Palsu(["ham", "spam", "phishing"], [[0.2, 0.3, 0.5]])
    b = Palsu(["phishing", "ham", "spam"], [[0.7, 0.1, 0.2]])
    assert np.allclose(proba_ensemble([a, b], ["teks"]), [[0.15, 0.25, 0.6]])


def test_putusan_ambang_inklusif_dan_seri_ham():
    p = np.array([[0.2, 0.3, 0.5], [0.4, 0.4, 0.2], [0.1, 0.5, 0.4]])
    assert putusan(p, 0.5).tolist() == ["phishing", "ham", "spam"]