"""Tes header keamanan (Tahap 11). Menguji MAKNA (isi kebijakan), bukan tata letak. Model SINTETIS."""
import pytest

from src.app import buat_app
from src.penilai import Penilai
from tests.test_penilai import ATURAN, _model


@pytest.fixture(scope="module")
def klien():
    return buat_app(penilai=Penilai([_model(0), _model(5), _model(9)], ATURAN)).test_client()


def _csp(resp):
    d = {}
    for bagian in resp.headers["Content-Security-Policy"].split(";"):
        kata = bagian.split()
        if kata:
            d[kata[0]] = kata[1:]
    return d


JALUR = [("GET", "/"), ("GET", "/health"), ("GET", "/samples"), ("GET", "/static/app.js"),
         ("GET", "/tidak-ada"), ("POST", "/health"), ("POST", "/analyze")]


@pytest.mark.parametrize("metode_jalur", JALUR)
def test_header_dasar_ada_di_semua_jawaban_termasuk_galat(klien, metode_jalur):
    metode, jalur = metode_jalur
    r = klien.open(jalur, method=metode)
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in r.headers


def test_csp_ketat_tanpa_sumber_luar_dan_tanpa_inline(klien):
    d = _csp(klien.get("/"))
    assert d["default-src"] == ["'self'"]
    for kunci in ("frame-ancestors", "object-src", "base-uri", "form-action"):
        assert d[kunci] == ["'none'"], kunci
    assert d.get("script-src", ["'self'"]) == ["'self'"] and d.get("style-src", ["'self'"]) == ["'self'"]
    semua = " ".join(" ".join(v) for v in d.values()).lower()
    for terlarang in ("unsafe-inline", "unsafe-eval", "http:", "https:", "*", "data:"):
        assert terlarang not in semua, terlarang


def test_header_ada_juga_di_galat_500():
    class Rusak:
        models = [object()]

        def nilai(self, teks):
            raise RuntimeError("x")

    r = buat_app(penilai=Rusak()).test_client().post("/analyze", json={"teks": "halo"})
    assert r.status_code == 500 and "Content-Security-Policy" in r.headers and r.headers["X-Frame-Options"] == "DENY"


def test_analyze_no_store_di_sukses_dan_galat(klien):
    assert klien.post("/analyze", json={"teks": "halo dunia"}).headers["Cache-Control"] == "no-store"
    assert klien.post("/analyze", json={"x": 1}).headers["Cache-Control"] == "no-store"
    assert klien.post("/analyze", json={"teks": "a" * 100_001}).headers["Cache-Control"] == "no-store"


def test_no_store_hanya_untuk_analyze(klien):
    assert "no-store" not in klien.get("/health").headers.get("Cache-Control", "")