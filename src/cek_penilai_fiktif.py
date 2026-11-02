"""Tahap 10a-2: kontrol regresi modul penilai pada 12 contoh FIKTIF terhadap Hasil 9-4 (docs/experiment_design.md).
Bukan evaluasi; tidak menyentuh data train atau test. Jalankan: python -m src.cek_penilai_fiktif"""
import json
from pathlib import Path

from src.penilai import STATUS_TIDAK as T
from src.penilai import muat_penilai

# id: (token, kata dikenal, putusan model, pita, "ham/spam/phishing", status) menurut Hasil 9-4
HASIL_94 = {
    "E01": (0, 0, "phishing", "HIGH", "0.31/0.17/0.52", T),
    "E02": (0, 0, "phishing", "HIGH", "0.31/0.17/0.52", T),
    "E03": (0, 0, "phishing", "HIGH", "0.31/0.17/0.52", T),
    "E04": (20, 4, "ham", "MEDIUM", "0.44/0.14/0.42", T),
    "E05": (23, 4, "ham", "MEDIUM", "0.51/0.13/0.36", T),
    "E06": (20, 5, "ham", "MEDIUM", "0.29/0.26/0.46", T),
    "E07": (4, 4, "spam", "MEDIUM", "0.24/0.26/0.50", T),
    "E08": (37, 36, "ham", "MEDIUM", "0.52/0.15/0.34", "MEDIUM"),
    "E09": (34, 31, "phishing", "HIGH", "0.00/0.00/1.00", "HIGH"),
    "E10": (32, 30, "spam", "LOW", "0.02/0.96/0.02", "LOW"),
    "E11": (29, 29, "phishing", "HIGH", "0.08/0.03/0.89", "HIGH"),
    "E12": (13, 9, "ham", "MEDIUM", "0.35/0.28/0.37", T),
}


def main():
    pen = muat_penilai()
    g = pen.aturan["gerbang_v2"]
    assert (g["n_min_kata_dikenal"], g["c_min_cakupan"]) == (16, 0.77), g
    contoh = json.loads(Path("samples/contoh_fiktif.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in contoh] == list(HASIL_94), "daftar contoh berubah"
    print("%-4s %4s %5s %-8s %-6s %-15s %-19s %s" % ("id", "tok", "kenal", "model", "pita", "P ham/spam/ph", "STATUS", "cocok 9-4"))
    hasil, beda = {}, 0
    for c in contoh:
        h = hasil[c["id"]] = pen.nilai(c["teks"])
        p = "/".join("%.2f" % h["p"][k] for k in ("ham", "spam", "phishing"))
        got = (h["n_token"], h["n_kenal"], h["putusan_model"], h["pita"], p, h["status"])
        cocok = got == HASIL_94[c["id"]]
        beda += not cocok
        print("%-4s %4d %5d %-8s %-6s %-15s %-19s %s" % (c["id"], got[0], got[1], got[2], got[3], p, got[5], "YA" if cocok else "BEDA %s" % (HASIL_94[c["id"]],)))
    assert hasil["E01"]["p"] == hasil["E02"]["p"] == hasil["E03"]["p"], "skor E01-E03 tidak identik"
    assert beda == 0, "%d dari 12 contoh berbeda dari Hasil 9-4" % beda
    print("KONTROL OK: 12 dari 12 contoh identik dengan Hasil 9-4; gerbang v2 = N_MIN 16, C_MIN 0.77")


if __name__ == "__main__":
    main()