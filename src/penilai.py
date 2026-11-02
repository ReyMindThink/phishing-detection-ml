"""Penilai (Tahap 10a): satu pintu untuk menilai teks dengan model beku, gerbang v2, dan pita risiko.
Skor = P(phishing) dari rata-rata 5 model (BUKAN probabilitas terkalibrasi). Status TIDAK DAPAT DINILAI
berarti periksa manual, BUKAN aman. Tidak mengunjungi URL, tidak menyimpan teks."""
import json
import re
from pathlib import Path

import numpy as np

from src.frozen_model import URUTAN, muat_ensemble, proba_ensemble, putusan

STATUS_TIDAK = "TIDAK DAPAT DINILAI"
ATURAN = "docs/app_rules.json"
LINK = re.compile(r"(?:https?|hxxps?)://\S+", re.IGNORECASE)
# Daftar FIKTIF tulis sendiri; TIDAK tervalidasi dan bukan dari test. Hanya penanda, bukan bukti.
KATA_MENDESAK = frozenset({"urgent", "immediately", "suspended", "suspension", "verify", "expires",
                           "expire", "expired", "locked", "deadline", "confirm", "alert"})


def lolos_gerbang(n_kenal, cakupan, aturan):
    """Gerbang v2 (bagian gerbang_v2; kunci tingkat atas = v1 yang tumpul dan TIDAK dipakai). Batas inklusif."""
    g = aturan["gerbang_v2"]
    return bool(n_kenal >= g["n_min_kata_dikenal"] and cakupan >= g["c_min_cakupan"])


def tentukan_pita(p_phishing, aturan):
    if p_phishing >= aturan["ambang_resmi"]:
        return "HIGH"
    return "MEDIUM" if p_phishing >= aturan["t_med"] else "LOW"


def hitung_link(teks):
    """Hitung penanda skema (http, https, hxxp, hxxps) dari teks; tidak mengunjungi apa pun."""
    return len(LINK.findall(teks))


def kata_mendesak(teks):
    return sorted(set(re.findall(r"[a-z]{3,}", teks.lower())) & KATA_MENDESAK)


class Penilai:
    def __init__(self, models, aturan):
        self.models, self.aturan = models, aturan
        self.token = re.compile(aturan["token_pattern"])
        self.kenal = set.intersection(*[set(m.named_steps["tfidf"].get_feature_names_out()) for m in models])

    def hitung_kata(self, teks):
        tok = self.token.findall(teks.lower())
        return len(tok), sum(w in self.kenal for w in tok)

    def kontribusi_semua(self, teks):
        """Rata-rata antar model dari koefisien x nilai TF-IDF untuk logit phishing; kata di luar kosakata sebuah model = 0."""
        total = {}
        for m in self.models:
            vec, clf = m.named_steps["tfidf"], m.named_steps["clf"]
            X = vec.transform([teks]).tocoo()
            nama, coef = vec.get_feature_names_out(), clf.coef_[list(clf.classes_).index("phishing")]
            for j, v in zip(X.col, X.data):
                total[nama[j]] = total.get(nama[j], 0.0) + float(coef[j] * v)
        return {k: v / len(self.models) for k, v in total.items()}

    def kontribusi(self, teks, top=10):
        semua = self.kontribusi_semua(teks)
        urut = sorted(semua.items(), key=lambda kv: kv[1])
        dorong = [{"kata": k, "nilai": v} for k, v in reversed(urut) if v > 0][:top]
        jauh = [{"kata": k, "nilai": v} for k, v in urut if v < 0][:top]
        return {"pendorong": dorong, "menjauhi": jauh}

    def nilai(self, teks):
        if not isinstance(teks, str):
            raise TypeError("teks harus string")
        n_tok, n_ken = self.hitung_kata(teks)
        cakupan = n_ken / max(n_tok, 1)
        lolos = lolos_gerbang(n_ken, cakupan, self.aturan)
        p = proba_ensemble(self.models, [teks])
        pita = tentukan_pita(float(p[0, 2]), self.aturan)
        return {"status": pita if lolos else STATUS_TIDAK, "lolos_gerbang": lolos, "pita": pita,
                "putusan_model": str(putusan(p, self.aturan["ambang_resmi"])[0]),
                "p": {k: float(v) for k, v in zip(URUTAN, p[0])},
                "n_token": n_tok, "n_kenal": n_ken, "cakupan": cakupan,
                "kontribusi": self.kontribusi(teks), "n_link": hitung_link(teks),
                "kata_mendesak": kata_mendesak(teks)}


def muat_penilai(path_manifest="docs/model_manifest.json", path_aturan=ATURAN):
    """Muat model HANYA lewat muat_ensemble (SHA256 diperiksa sebelum joblib.load)."""
    models, _ = muat_ensemble(path_manifest)
    aturan = json.loads(Path(path_aturan).read_text(encoding="utf-8"))
    return Penilai(models, aturan)