"""Tahap 9-3: turunkan pita risiko dan gerbang masukan dari data TRAIN (OOF dari 5 model beku; test tidak disentuh).
KONTROL: OOF argmax 3245/1317/2584 dan tp/n_pred 2513/2549 pada ambang turunan ulang.
Mencetak agregat saja dan menulis docs/app_rules.json (angka saja). Jalankan: python -m src.derive_app_rules"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from src.frozen_model import URUTAN, muat_ensemble

TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
TARGET_MED = 0.99


def hitung_token(teks, kenal):
    n_tok, n_ken = [], []
    for s in teks:
        tok = re.findall(TOKEN, s.lower())
        n_tok.append(len(tok))
        n_ken.append(sum(w in kenal for w in tok))
    return np.array(n_tok), np.array(n_ken)


def gerbang(n_tok, n_ken, y):
    cov = n_ken / np.maximum(n_tok, 1)
    n_min = max(1, int(np.floor(np.percentile(n_ken, 1))))
    c_min = float(np.floor(np.percentile(cov, 1) * 100 + 1e-9) / 100)
    lolos = (n_ken >= n_min) & (cov >= c_min)
    print("GERBANG: N_MIN=%d, C_MIN=%.2f; lolos gabungan %.2f%% (%d dari %d)" % (n_min, c_min, 100 * lolos.mean(), lolos.sum(), len(y)))
    for k in URUTAN:
        m = y == k
        p = np.percentile(n_ken[m], [1, 5, 50])
        print("  %-9s lolos %.2f%% (n=%d); persentil 1/5/50 kata dikenal: %s" % (k, 100 * lolos[m].mean(), m.sum(), "/".join("%.0f" % v for v in p)))
    return n_min, c_min


def pita(P, y, t, t_med):
    batas = {"HIGH": P >= t, "MEDIUM": (P >= t_med) & (P < t), "LOW": P < t_med}
    print("PITA (OOF train, model tunggal per lipatan; INDIKATIF; skor bukan probabilitas):")
    hasil = {}
    for nama, m in batas.items():
        c = [int((m & (y == k)).sum()) for k in URUTAN]
        n = sum(c)
        print("  %-7s n=%4d%s  ham %d, spam %d, phishing %d -> %.1f%% phishing" % (nama, n, "*" if n < 30 else "", *c, 100 * c[2] / max(n, 1)))
        hasil[nama] = dict(zip(["n_ham", "n_spam", "n_phishing"], c))
    return hasil


def hitung(models, teks, y, fold, ambang, kontrol=True):
    P, ph = np.zeros((len(y), 3)), y == "phishing"
    for k, m in enumerate(models):
        va = fold == k
        P[va] = m.predict_proba(teks[va])[:, [list(m.classes_).index(c) for c in URUTAN]]
    t = float(np.sort(P[ph, 2])[::-1][int(np.ceil(0.93 * ph.sum())) - 1])
    if kontrol:
        cm = confusion_matrix(y, np.array(URUTAN)[P.argmax(axis=1)], labels=URUTAN)
        assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
        tp, n_pred = int(((P[:, 2] >= t) & ph).sum()), int((P[:, 2] >= t).sum())
        assert abs(t - ambang) < 1e-9 and (tp, n_pred) == (2513, 2549), (t, tp, n_pred)
        print("KONTROL OK: OOF 3245/1317/2584; ambang turunan ulang %.16f (selisih ke manifest %.2g); 2513/2549" % (t, t - ambang))
    t_med = float(np.sort(P[ph, 2])[::-1][int(np.ceil(TARGET_MED * ph.sum())) - 1])
    print("t_med (target recall %.2f) = %.4f; ambang resmi = %.4f" % (TARGET_MED, t_med, t))
    jml = pita(P[:, 2], y, t, t_med)
    kenal = set.intersection(*[set(m.named_steps["tfidf"].get_feature_names_out()) for m in models])
    n_min, c_min = gerbang(*hitung_token(teks, kenal), y)
    return {"tahap": "9-3", "ambang_resmi": ambang, "t_med": t_med, "target_recall_medium": TARGET_MED,
            "n_min_kata_dikenal": n_min, "c_min_cakupan": c_min, "n_kata_dikenal": len(kenal),
            "token_pattern": TOKEN, "pita_oof_train": jml,
            "catatan": "diturunkan dari data TRAIN; pita indikatif; skor bukan probabilitas terkalibrasi"}


def main():
    df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False, usecols=["content_hash", "label", "body_text"])
    sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
    df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
    assert df["split"].notna().all(), "ada email tanpa indeks split"
    df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
    assert len(df) == 7438, len(df)
    models, manifest = muat_ensemble()
    aturan = hitung(models, df["body_text"], df["label"].to_numpy(), df["fold"].to_numpy(), manifest["ambang"])
    Path("docs/app_rules.json").write_text(json.dumps(aturan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ditulis: docs/app_rules.json")


if __name__ == "__main__":
    main()