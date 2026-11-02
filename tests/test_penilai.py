"""Tes modul penilai (Tahap 10a). Memakai model SINTETIS kecil; tidak bergantung pada models/ atau data/."""
import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.derive_app_rules import hitung_token
from src.frozen_model import sha256_file
from src.penilai import (STATUS_TIDAK, Penilai, hitung_link, kata_mendesak, lolos_gerbang, muat_penilai,
                         tentukan_pita)

TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
# Kunci tingkat atas (n_min 1, c_min 0.0) = umpan v1 yang tumpul: penilai TIDAK boleh membacanya.
ATURAN = {"ambang_resmi": 0.5, "t_med": 0.2, "token_pattern": TOKEN,
          "n_min_kata_dikenal": 1, "c_min_cakupan": 0.0,
          "gerbang_v2": {"n_min_kata_dikenal": 3, "c_min_cakupan": 0.5}}
HAM = ["team meeting about project schedule and office lunch", "please review the report before the meeting tomorrow",
       "agenda for the project team meeting and lunch plan", "the office schedule for tomorrow is ready for review"]
SPAM = ["free offer winner claim your prize now cheap deal", "cheap deal free prize winner claim offer today",
        "win free prize with this cheap offer claim now", "limited offer free winner cheap prize deal today"]
PHISH = ["verify your account password bank login urgent security update", "urgent your bank account suspended verify password now",
         "security alert verify your online banking account password", "update your account password to avoid suspension of your bank card"]
TEKS_PHISH = "urgent verify your bank account password"


def _model(lewati):
    teks = HAM + SPAM + PHISH
    y = ["ham"] * 4 + ["spam"] * 4 + ["phishing"] * 4
    ada = [i for i in range(12) if i != lewati]
    m = Pipeline([("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=1, sublinear_tf=True)),
                  ("clf", LogisticRegression(C=10, max_iter=1000, random_state=42))])
    m.fit([teks[i] for i in ada], [y[i] for i in ada])
    return m


@pytest.fixture(scope="module")
def penilai():
    return Penilai([_model(0), _model(5), _model(9)], ATURAN)


def test_gerbang_pakai_v2_bukan_kunci_atas_dan_inklusif():
    assert lolos_gerbang(3, 0.5, ATURAN) is True
    assert lolos_gerbang(2, 1.0, ATURAN) is False      # kunci atas (n_min 1) akan meloloskan: salah
    assert lolos_gerbang(10, 0.49, ATURAN) is False


def test_pita_batas_inklusif():
    assert tentukan_pita(0.5, ATURAN) == "HIGH"
    assert tentukan_pita(0.4999, ATURAN) == "MEDIUM"
    assert tentukan_pita(0.2, ATURAN) == "MEDIUM"
    assert tentukan_pita(0.1999, ATURAN) == "LOW"


def test_hitung_link_termasuk_defanged_tanpa_link():
    assert hitung_link("buka hxxps://contoh[.]com dan http://example.com sekarang") == 2
    assert hitung_link("tidak ada tautan di sini, hanya example.com") == 0


def test_kata_mendesak_unik_terurut_huruf_besar_kecil():
    assert kata_mendesak("URGENT: verify now, verify again") == ["urgent", "verify"]
    assert kata_mendesak("jadwal rapat besok") == []


def test_hitung_kata_sama_dengan_hitung_token_lama(penilai):
    for t in ["", "   ", "12345", TEKS_PHISH, "Meeting TOMORROW at the office, zzzz qqqq"]:
        n_tok, n_ken = hitung_token([t], penilai.kenal)
        assert penilai.hitung_kata(t) == (int(n_tok[0]), int(n_ken[0]))


@pytest.mark.parametrize("teks", ["", "   ", "12345"])
def test_teks_kosong_spasi_angka_tidak_dapat_dinilai(penilai, teks):
    h = penilai.nilai(teks)
    assert h["status"] == STATUS_TIDAK and h["lolos_gerbang"] is False
    assert h["n_token"] == 0 and h["cakupan"] == 0.0 and h["kontribusi"] == {"pendorong": [], "menjauhi": []}


def test_sedikit_kata_dikenal_ditahan_walau_kunci_atas_meloloskan(penilai):
    h = penilai.nilai("bank zzzz qqqq wwww xxxx")
    assert h["n_kenal"] >= 1 and h["status"] == STATUS_TIDAK


def test_teks_phishing_lolos_gerbang_dan_konsisten(penilai):
    h = penilai.nilai(TEKS_PHISH)
    assert h["lolos_gerbang"] is True and h["status"] == h["pita"]
    assert abs(sum(h["p"].values()) - 1.0) < 1e-9
    assert (h["putusan_model"] == "phishing") == (h["p"]["phishing"] >= ATURAN["ambang_resmi"])
    assert h["pita"] == tentukan_pita(h["p"]["phishing"], ATURAN)
    assert h["kata_mendesak"] == ["urgent", "verify"]


def test_ham_dan_spam_tidak_berpita_high(penilai):
    assert penilai.nilai("the team meeting agenda for tomorrow office lunch")["pita"] != "HIGH"
    assert penilai.nilai("free cheap prize winner claim offer deal today")["putusan_model"] == "spam"


def test_kontribusi_urutan_tanda_dan_batas(penilai):
    k = penilai.kontribusi(TEKS_PHISH + " meeting agenda", top=3)
    assert len(k["pendorong"]) <= 3 and len(k["menjauhi"]) <= 3
    assert all(d["nilai"] > 0 for d in k["pendorong"]) and all(d["nilai"] < 0 for d in k["menjauhi"])
    nilai = [d["nilai"] for d in k["pendorong"]]
    assert nilai == sorted(nilai, reverse=True)
    assert "password" in [d["kata"] for d in k["pendorong"]]


def test_kontrol_numerik_kontribusi_dijumlah_sama_dengan_logit(penilai):
    """Kontrol (seperti 9-1): jumlah kontribusi + intercept = decision_function phishing (rata-rata antar model)."""
    for t in [TEKS_PHISH, "meeting agenda for the project", "free prize and bank zzzz"]:
        semua = penilai.kontribusi_semua(t)
        logit = np.mean([m.decision_function([t])[0, list(m.named_steps["clf"].classes_).index("phishing")]
                         for m in penilai.models])
        icpt = np.mean([m.named_steps["clf"].intercept_[list(m.named_steps["clf"].classes_).index("phishing")]
                        for m in penilai.models])
        assert abs(sum(semua.values()) + icpt - logit) < 1e-9


def test_nilai_menolak_masukan_bukan_string(penilai):
    for bad in [None, 123, ["a"]]:
        with pytest.raises(TypeError):
            penilai.nilai(bad)


def _tulis_manifest(d, sha_salah):
    paths, models = [], []
    for i, lewati in enumerate((0, 5, 9)):
        p = Path(d) / ("m%d.joblib" % i)
        joblib.dump(_model(lewati), p)
        models.append({"path": str(p), "sha256": ("0" * 64) if (sha_salah and i == 1) else sha256_file(p)})
    man = Path(d) / "manifest.json"
    man.write_text(json.dumps({"models": models}), encoding="utf-8")
    ar = Path(d) / "aturan.json"
    ar.write_text(json.dumps(ATURAN), encoding="utf-8")
    return man, ar


def test_muat_penilai_hash_cocok_berhasil():
    with tempfile.TemporaryDirectory() as d:
        man, ar = _tulis_manifest(d, sha_salah=False)
        assert len(muat_penilai(man, ar).models) == 3


def test_muat_penilai_hash_salah_menolak():
    with tempfile.TemporaryDirectory() as d:
        man, ar = _tulis_manifest(d, sha_salah=True)
        with pytest.raises(ValueError):
            muat_penilai(man, ar)