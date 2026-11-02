"""Tes API Flask (Tahap 10b). Memakai model SINTETIS; tidak bergantung pada models/ atau data/."""
import json
import tempfile
from unittest import mock

import pytest

from src.app import buat_app, main
from src.penilai import Penilai
from tests.test_penilai import ATURAN, TEKS_PHISH, _model, _tulis_manifest


@pytest.fixture(scope="module")
def klien():
    pen = Penilai([_model(0), _model(5), _model(9)], ATURAN)
    return buat_app(penilai=pen).test_client()


def test_health(klien):
    r = klien.get("/health")
    assert r.status_code == 200 and r.get_json() == {"layanan": "hidup", "n_model": 3}


def test_samples_default_memuat_12_contoh_fiktif(klien):
    r = klien.get("/samples")
    contoh = r.get_json()
    assert r.status_code == 200 and [c["id"] for c in contoh] == ["E%02d" % i for i in range(1, 13)]
    assert all(set(c) == {"id", "kelompok", "teks"} for c in contoh)


def test_analyze_teks_phishing_lengkap_dan_berkatatan(klien):
    r = klien.post("/analyze", json={"teks": TEKS_PHISH})
    h = r.get_json()
    assert r.status_code == 200 and h["status"] in {"HIGH", "MEDIUM", "LOW"}
    assert set(h) >= {"status", "pita", "p", "putusan_model", "n_kenal", "cakupan", "kontribusi", "n_link",
                      "kata_mendesak", "catatan"}
    assert "BUKAN probabilitas" in h["catatan"] and "periksa manual" in h["catatan"]


def test_analyze_teks_kosong_tidak_dapat_dinilai(klien):
    h = klien.post("/analyze", json={"teks": ""}).get_json()
    assert h["status"] == "TIDAK DAPAT DINILAI"


@pytest.mark.parametrize("badan", [{}, {"teks": 5}, {"teks": None}, ["teks"], "halo"])
def test_analyze_masukan_salah_ditolak_400(klien, badan):
    r = klien.post("/analyze", json=badan)
    assert r.status_code == 400 and "error" in r.get_json()


def test_analyze_bukan_json_ditolak_400(klien):
    r = klien.post("/analyze", data="halo", content_type="text/plain")
    assert r.status_code == 400


def test_galat_berupa_json(klien):
    r = klien.get("/analyze")
    assert r.status_code == 405 and "error" in r.get_json()
    r = klien.get("/tidak-ada")
    assert r.status_code == 404 and "error" in r.get_json()


def test_masukan_tidak_dipantulkan_kembali(klien):
    r = klien.post("/analyze", json={"teks": "zzqmarkerzz <script>alert(1)</script> urgent"})
    assert "zzqmarkerzz" not in r.get_data(as_text=True) and "<script>" not in r.get_data(as_text=True)


def test_startup_hash_salah_menolak_jalan():
    with tempfile.TemporaryDirectory() as d:
        man, ar = _tulis_manifest(d, sha_salah=True)
        with pytest.raises(ValueError):
            buat_app(path_manifest=man, path_aturan=ar)


def test_startup_hash_cocok_berjalan_dan_menilai():
    with tempfile.TemporaryDirectory() as d:
        man, ar = _tulis_manifest(d, sha_salah=False)
        r = buat_app(path_manifest=man, path_aturan=ar).test_client().post("/analyze", json={"teks": TEKS_PHISH})
        assert r.status_code == 200 and json.loads(r.get_data())["status"] in {"HIGH", "MEDIUM", "LOW"}


def test_main_hanya_localhost_tanpa_debug():
    with mock.patch("src.app.buat_app") as b:
        main()
    b.return_value.run.assert_called_once_with(host="127.0.0.1", port=5000, debug=False)