"""Tahap 9-4: uji perilaku pada 12 contoh FIKTIF (samples/contoh_fiktif.json): gerbang v1 dan v2, skor model, pita.
Bukan evaluasi statistik; tidak memakai data train atau test. Jalankan: python -m src.uji_fiktif"""
import json
from pathlib import Path

import numpy as np

from src.derive_app_rules import hitung_token
from src.frozen_model import muat_ensemble, proba_ensemble


def nilai_satu(teks, models, kenal, aturan):
    n_tok, n_ken = (int(v[0]) for v in hitung_token([teks], kenal))
    cov, g2 = n_ken / max(n_tok, 1), aturan["gerbang_v2"]
    v1 = n_ken >= aturan["n_min_kata_dikenal"] and cov >= aturan["c_min_cakupan"]
    v2 = n_ken >= g2["n_min_kata_dikenal"] and cov >= g2["c_min_cakupan"]
    p = proba_ensemble(models, [teks])[0]
    pita = "HIGH" if p[2] >= aturan["ambang_resmi"] else "MEDIUM" if p[2] >= aturan["t_med"] else "LOW"
    putusan = "phishing" if p[2] >= aturan["ambang_resmi"] else ("ham" if p[0] >= p[1] else "spam")
    return {"n_tok": n_tok, "n_ken": n_ken, "cov": cov, "v1": v1, "v2": v2, "p": p, "putusan": putusan,
            "pita": pita, "status": pita if v2 else "TIDAK DAPAT DINILAI"}


def main():
    models, _ = muat_ensemble()
    aturan = json.loads(Path("docs/app_rules.json").read_text(encoding="utf-8"))
    contoh = json.loads(Path("samples/contoh_fiktif.json").read_text(encoding="utf-8"))
    kenal = set.intersection(*[set(m.named_steps["tfidf"].get_feature_names_out()) for m in models])
    hasil = {c["id"]: nilai_satu(c["teks"], models, kenal, aturan) for c in contoh}
    p1, p2, p3 = (hasil[i]["p"] for i in ("E01", "E02", "E03"))
    assert np.allclose(p1, p2, atol=1e-12) and np.allclose(p1, p3, atol=1e-12), (p1, p2, p3)
    assert abs(p1[2] - 0.5158) < 1e-4, p1
    print("KONTROL OK: E01-E03 skor identik %s (P phishing 0.5158 seperti temuan 8-5)" % np.round(p1, 4))
    print("%-4s %-31s %4s %5s %5s %2s %2s %-17s %-8s %-6s %s" % ("id", "kelompok", "tok", "kenal", "cakup", "v1", "v2", "P ham/spam/phish", "model", "pita", "STATUS"))
    for c in contoh:
        h = hasil[c["id"]]
        print("%-4s %-31s %4d %5d %5.2f %2s %2s %-17s %-8s %-6s %s" % (c["id"], c["kelompok"], h["n_tok"], h["n_ken"], h["cov"],
              "Y" if h["v1"] else "T", "Y" if h["v2"] else "T", "/".join("%.2f" % v for v in h["p"]), h["putusan"], h["pita"], h["status"]))


if __name__ == "__main__":
    main()