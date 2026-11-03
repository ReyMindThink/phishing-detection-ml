"""Tes privasi dan jenis konten (Tahap 11). Model SINTETIS."""
import json

import pytest

from src.app import buat_app
from src.penilai import Penilai
from tests.test_penilai import ATURAN, _model


@pytest.fixture(scope="module")
def klien():
    return buat_app(penilai=Penilai([_model(0), _model(5), _model(9)], ATURAN)).test_client()


def test_isi_masukan_tidak_muncul_di_log_pada_sukses_400_dan_413(klien, caplog):
    penanda = "zzqpenandarahasiazz"
    with caplog.at_level("DEBUG"):
        assert klien.post("/analyze", json={"teks": penanda}).status_code == 200
        assert klien.post("/analyze", json={"teks": [penanda]}).status_code == 400
        assert klien.post("/analyze", json={"teks": penanda * 20_000}).status_code == 413
    assert penanda not in caplog.text


@pytest.mark.parametrize("jenis", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data"])
def test_json_valid_dengan_jenis_konten_non_json_ditolak_400(klien, jenis):
    r = klien.post("/analyze", data=json.dumps({"teks": "halo dunia"}), content_type=jenis)
    assert r.status_code == 400