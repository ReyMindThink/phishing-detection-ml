"""Tes statis UI (Tahap 10c): berkas halaman disajikan, tanpa klaim 'aman', tanpa cara menyisipkan HTML. Bukan tes browser."""
import re
from pathlib import Path

import pytest

from src.app import buat_app
from src.penilai import Penilai
from tests.test_penilai import ATURAN, _model

STATIK = Path(__file__).resolve().parent.parent / "src" / "static"
BERKAS = ["index.html", "app.js", "style.css"]
KLAIM = re.compile(r"\b(aman|secure|protected|safe)\b", re.IGNORECASE)
SISIP = ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"]


@pytest.fixture(scope="module")
def klien():
    return buat_app(penilai=Penilai([_model(0), _model(5), _model(9)], ATURAN)).test_client()


def _baca(nama):
    return (STATIK / nama).read_text(encoding="utf-8")


def test_halaman_dan_berkas_statis_disajikan(klien):
    r = klien.get("/")
    assert r.status_code == 200 and "text/html" in r.content_type and b"Penilai Risiko Email" in r.data
    for nama in ("app.js", "style.css"):
        assert klien.get("/static/" + nama).status_code == 200


def test_tanpa_skrip_atau_gaya_sebaris():
    html = _baca("index.html")
    assert re.findall(r"<script(?![^>]*\bsrc=)", html) == [] and "<style" not in html and " style=" not in html


@pytest.mark.parametrize("nama", BERKAS)
def test_tanpa_klaim_aman_secure_atau_protected(nama):
    assert KLAIM.findall(_baca(nama)) == []


@pytest.mark.parametrize("nama", ["index.html", "app.js"])
def test_tanpa_klaim_seratus_persen_di_teks_halaman(nama):
    assert not re.search(r"100\s*%", _baca(nama))


def test_app_js_tidak_menyisipkan_html():
    js = _baca("app.js")
    assert [k for k in SISIP if k in js] == []


def _datar(teks):
    return " ".join(teks.split()).lower()


def _kunci(teks, nama):
    return re.search(r"""["']?%s["']?\s*:""" % re.escape(nama), teks) is not None


def test_peringatan_wajib_ada_di_halaman():
    semua = _datar(_baca("index.html") + " " + _baca("app.js"))
    for frasa in ("2002-2007", "bukan alat keamanan utama", "periksa manual", "bukan probabilitas"):
        assert frasa in semua, frasa


def test_semua_status_dan_tiga_contoh_terhubung():
    js, html = _baca("app.js"), _baca("index.html")
    for status in ("HIGH", "MEDIUM", "LOW", "TIDAK DAPAT DINILAI"):
        assert _kunci(js, status), status
    for kode in ("E08", "E09", "E11"):
        assert 'data-id="%s"' % kode in html and _kunci(js, kode), kode