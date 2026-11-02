"""Tes batas ukuran input dan galat tak terduga (Tahap 11). Model SINTETIS; tidak bergantung pada models/ atau data/."""
import json

import pytest

from src.app import buat_app
from src.penilai import Penilai
from tests.test_penilai import ATURAN, _model


@pytest.fixture(scope="module")
def klien():
    return buat_app(penilai=Penilai([_model(0), _model(5), _model(9)], ATURAN)).test_client()


def test_batas_teks_100000_karakter_lolos_dan_di_atasnya_413(klien):
    assert klien.post("/analyze", json={"teks": "a" * 100_000}).status_code == 200
    r = klien.post("/analyze", json={"teks": "a" * 100_001})
    assert r.status_code == 413 and "error" in r.get_json()


def test_karakter_di_luar_bmp_di_batas_teks_lolos_walau_badan_besar(klien):
    badan = json.dumps({"teks": "\U0001F600" * 100_000})
    assert len(badan) > 1_000_000
    r = klien.post("/analyze", data=badan, content_type="application/json")
    assert r.status_code == 200


def test_badan_di_atas_batas_byte_ditolak_413_json(klien):
    badan = json.dumps({"teks": "a", "lain": "b" * 1_250_000})
    r = klien.post("/analyze", data=badan, content_type="application/json")
    assert r.status_code == 413 and "error" in r.get_json()


class _PenilaiRusak:
    models = [object()]

    def nilai(self, teks):
        raise RuntimeError("RAHASIA-INTERNAL " + teks)


def test_galat_tak_terduga_500_json_tanpa_detail_dan_tanpa_isi_di_log(caplog):
    k = buat_app(penilai=_PenilaiRusak()).test_client()
    with caplog.at_level("DEBUG"):
        r = k.post("/analyze", json={"teks": "zzqmarkerzz"})
    assert r.status_code == 500 and r.get_json() == {"error": "Internal Server Error"}
    assert "RAHASIA-INTERNAL" not in r.get_data(as_text=True) and "Traceback" not in r.get_data(as_text=True)
    assert "zzqmarkerzz" not in caplog.text and "RAHASIA-INTERNAL" not in caplog.text