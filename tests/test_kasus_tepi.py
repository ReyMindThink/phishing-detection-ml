"""Tes kasus tepi (Tahap 12). Model SINTETIS; tidak bergantung pada models/ atau data/.
Tes bernama *_perilaku_saat_ini adalah KARAKTERISASI temuan (bukan perilaku yang diinginkan); lihat Hasil Tahap 12."""
import json
from email import message_from_bytes, message_from_string
from pathlib import Path

import pytest

from src.app import buat_app
from src.email_parser import ekstrak_metadata, fitur_link, parse_pesan
from src.penilai import STATUS_TIDAK, Penilai, hitung_link
from tests.test_penilai import ATURAN, HAM, _model

HTML = '<p>halo <a href="http://example.com/x">klik</a></p>'
BADAN_CT_RUSAK = "text/html content-transfer-encoding: 8bit"


@pytest.fixture(scope="module")
def penilai():
    return Penilai([_model(0), _model(5), _model(9)], ATURAN)


def test_content_type_rusak_mengosongkan_badan_perilaku_saat_ini():
    normal = message_from_string("From: a@example.com\nContent-Type: text/html\n\n" + HTML)
    rusak = message_from_string(f"From: a@example.com\nContent-Type: {BADAN_CT_RUSAK}\n\n" + HTML)
    assert "halo" in parse_pesan(normal)["body_text"] and fitur_link(normal)["n_links"] == 1  # kontrol
    assert parse_pesan(rusak)["body_text"] == "" and fitur_link(rusak)["n_links"] == 0
    assert ekstrak_metadata(rusak)["content_type"] == BADAN_CT_RUSAK


def test_host_unicode_mentah_tidak_ditandai_punycode_perilaku_saat_ini():
    isi = "lihat http://xn--pple-43d.example/a dan http://\u0430pple.example/b".encode("utf-8")
    pesan = message_from_bytes(b"From: a@example.com\nContent-Type: text/plain; charset=utf-8\n"
                               b"Content-Transfer-Encoding: 8bit\n\n" + isi)
    f = fitur_link(pesan)
    assert "\u0430" in f["domains_link_defanged"]  # kontrol: huruf Unicode benar-benar sampai ke parser
    assert f["n_links"] == 2 and f["n_link_punycode"] == 1


@pytest.mark.parametrize("pesan,teks", [
    ("From: a@example.com\nContent-Type: \n\nteks biasa", "teks biasa"),
    ("From: a@example.com\nContent-Type: text/plain; charset=unknown-8bit\n\nhalo dunia", "halo dunia"),
    ("\n\nhanya badan", "hanya badan"),
    ("", ""),
])
def test_header_aneh_atau_pesan_kosong_tidak_error(pesan, teks):
    assert parse_pesan(message_from_string(pesan))["body_text"] == teks


def test_hitung_link_url_unicode_punycode_dan_tautan_tanpa_skema():
    teks = "http://xn--pple-43d.example http://\u0430pple.example hxxp://x.y example.com www.example.com"
    assert hitung_link(teks) == 3  # tautan tanpa skema TIDAK dihitung (keterbatasan yang diketahui)


def test_email_tanpa_link_n_link_nol(penilai):
    assert penilai.nilai(HAM[1])["n_link"] == 0


def test_teks_indonesia_fiktif_e04_e06_ditahan_gerbang_pada_model_sintetis(penilai):
    contoh = {c["id"]: c["teks"] for c in json.loads(Path("samples/contoh_fiktif.json").read_text(encoding="utf-8"))}
    for id_ in ("E04", "E05", "E06"):
        h = penilai.nilai(contoh[id_])
        assert h["lolos_gerbang"] is False and h["status"] == STATUS_TIDAK, id_


@pytest.mark.parametrize("teks", ["\ud800" * 10, "\x00" * 5000, "a\u200bb " * 100, "\u202e" * 50 + "halo",
                                  "\U0001F600" * 100, "a\r\nb\r\n" * 50, "\t" * 100],
                         ids=["surrogat", "nul", "lebar-nol", "rtl", "emoji", "crlf", "tab"])
def test_masukan_aneh_dijawab_200_dengan_bentuk_stabil(penilai, teks):
    k = buat_app(penilai=penilai).test_client()
    r = k.post("/analyze", data=json.dumps({"teks": teks}), content_type="application/json")
    j = r.get_json()
    assert r.status_code == 200 and "p" in j
    assert j["status"] in ("HIGH", "MEDIUM", "LOW", STATUS_TIDAK)