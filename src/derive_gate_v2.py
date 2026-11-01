"""Tahap 9-3c: gerbang masukan v2 (persentil ke-5; dirancang SETELAH melihat hasil 9-3, jadi EKSPLORATIF).
Data TRAIN saja (test tidak disentuh). KONTROL: persentil 1 mereproduksi 9-3 (N_MIN=1, C_MIN=0,00, lolos 7351).
Menambah bagian gerbang_v2 ke docs/app_rules.json. Jalankan: python -m src.derive_gate_v2"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.derive_app_rules import hitung_token
from src.frozen_model import URUTAN, muat_ensemble

PERSENTIL = 5
JSON_PATH = "docs/app_rules.json"


def turunkan(n_tok, n_ken, persen):
    cov = n_ken / np.maximum(n_tok, 1)
    n_min = max(1, int(np.floor(np.percentile(n_ken, persen))))
    c_min = float(np.floor(np.percentile(cov, persen) * 100 + 1e-9) / 100)
    return n_min, c_min, cov, (n_ken >= n_min), (cov >= c_min)


def laporkan(n_tok, n_ken, y):
    n_min, c_min, cov, ok_n, ok_c = turunkan(n_tok, n_ken, PERSENTIL)
    lolos = ok_n & ok_c
    print("GERBANG v2 (persentil ke-%d): N_MIN=%d, C_MIN=%.2f; lolos gabungan %.2f%% (%d dari %d)" % (PERSENTIL, n_min, c_min, 100 * lolos.mean(), lolos.sum(), len(y)))
    print("  gagal karena kata dikenal saja %d, cakupan saja %d, keduanya %d" % ((~ok_n & ok_c).sum(), (ok_n & ~ok_c).sum(), (~ok_n & ~ok_c).sum()))
    for k in URUTAN:
        m = y == k
        pc = np.percentile(cov[m], [1, 5, 50])
        print("  %-9s lolos %.2f%% (n=%d, gagal %d); persentil 1/5/50 cakupan: %s" % (k, 100 * lolos[m].mean(), m.sum(), (~lolos[m]).sum(), "/".join("%.2f" % v for v in pc)))
    return {"persentil": PERSENTIL, "n_min_kata_dikenal": n_min, "c_min_cakupan": c_min,
            "lolos_train_persen": round(100 * float(lolos.mean()), 2),
            "catatan": "dirancang setelah melihat hasil 9-3; eksploratif; hanya kosakata Inggris yang dikenal, bukan makna"}


def main():
    df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False, usecols=["content_hash", "label", "body_text"])
    sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
    df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
    assert df["split"].notna().all(), "ada email tanpa indeks split"
    df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
    assert len(df) == 7438, len(df)
    models, _ = muat_ensemble()
    kenal = set.intersection(*[set(m.named_steps["tfidf"].get_feature_names_out()) for m in models])
    n_tok, n_ken = hitung_token(df["body_text"], kenal)
    n1, c1, _, ok_n, ok_c = turunkan(n_tok, n_ken, 1)
    assert (n1, c1, int((ok_n & ok_c).sum())) == (1, 0.0, 7351), (n1, c1, int((ok_n & ok_c).sum()))
    print("KONTROL OK: persentil 1 = hasil 9-3 (N_MIN=1, C_MIN=0.00, lolos 7351 dari 7438)")
    v2 = laporkan(n_tok, n_ken, df["label"].to_numpy())
    aturan = json.loads(Path(JSON_PATH).read_text(encoding="utf-8"))
    aturan["gerbang_v2"] = v2
    Path(JSON_PATH).write_text(json.dumps(aturan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ditulis: %s (bagian gerbang_v2)" % JSON_PATH)


if __name__ == "__main__":
    main()