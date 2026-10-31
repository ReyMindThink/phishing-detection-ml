"""Tahap 9-2: ablasi kata teratas dengan kontrol acak (OOF, data TRAIN saja; test tidak disentuh).
Model = konfigurasi model beku (TF-IDF + LogReg C=1) dilatih ulang per lipatan dengan kata dibuang dari kosakata.
KONTROL: BASE mereproduksi OOF 3245/1317/2584 dan 2513/2549. Hanya angka agregat yang dicetak.
Jalankan: python -m src.ablate_top_words (lama: puluhan model dilatih; tunggu prompt kembali)"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix
from sklearn.pipeline import Pipeline

from src.frozen_model import MANIFEST, URUTAN

TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
JAUH = ("list www listinfo mailman url wrote fork remove xent newsisfree linux mailing removed free "
        "subject net lists spamassassin http date").split()
PHISH = ("account ebay paypal she bank customer dear annie online security thank paul him his banking "
         "your please update had card").split()
N_ACAK, N_JOBS = 5, 4


def latih_fold(teks, y, fold, k, stop):
    va = fold == k
    m = Pipeline([("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3, max_features=20000,
                                            sublinear_tf=True, stop_words=list(stop) or None)),
                  ("clf", LogisticRegression(max_iter=1000, random_state=42))])
    m.fit(teks[~va], y[~va])
    return k, m.predict_proba(teks[va])[:, [list(m.classes_).index(c) for c in URUTAN]]


def kata_acak(vocab, df_kata, target, seed):
    """Satu kata acak per kata target dengan df mirip (selisih relatif <= 20%), di luar kata target."""
    rng, indeks = np.random.default_rng(seed), {w: i for i, w in enumerate(vocab)}
    dilarang, pilih = set(JAUH + PHISH), []
    for w in target:
        d = df_kata[indeks[w]]
        ok = np.flatnonzero(np.abs(df_kata - d) <= 0.2 * d)
        ok = [i for i in ok if vocab[i] not in dilarang and vocab[i] not in pilih]
        assert ok, "tidak ada kandidat acak untuk %s" % w
        pilih.append(vocab[int(rng.choice(ok))])
    return pilih


def metrik(P, ph, ambang):
    pred = P[:, 2] >= ambang
    return average_precision_score(ph, P[:, 2]), (pred & ph).sum() / ph.sum(), int((pred & ~ph).sum())


def jalankan(teks, y, fold, ambang, kontrol=True):
    ph = y == "phishing"
    cv = CountVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3, binary=True).fit(teks)
    vocab, df_kata = cv.get_feature_names_out(), np.asarray(cv.transform(teks).sum(axis=0)).ravel()
    konf = {"BASE": []}
    for nama, tgt in (("JAUH", JAUH), ("PHISH", PHISH), ("GABUNG", JAUH + PHISH)):
        konf[nama] = tgt
        for s in range(N_ACAK):
            konf["%s_acak%d" % (nama, s)] = kata_acak(vocab, df_kata, tgt, s)
    tugas = [(n, k) for n in konf for k in range(5)]
    hasil = Parallel(n_jobs=N_JOBS)(delayed(latih_fold)(teks, y, fold, k, konf[n]) for n, k in tugas)
    oof = {n: np.zeros((len(y), 3)) for n in konf}
    for (n, k), (_, p) in zip(tugas, hasil):
        oof[n][fold == k] = p
    if kontrol:
        cm = confusion_matrix(y, np.array(URUTAN)[oof["BASE"].argmax(axis=1)], labels=URUTAN)
        assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
        t = float(np.sort(oof["BASE"][ph, 2])[::-1][int(np.ceil(0.93 * ph.sum())) - 1])
        tp, n_pred = int(((oof["BASE"][:, 2] >= t) & ph).sum()), int((oof["BASE"][:, 2] >= t).sum())
        assert abs(t - ambang) < 1e-9 and (tp, n_pred) == (2513, 2549), (t, tp, n_pred)
        print("KONTROL OK: BASE = OOF 3245/1317/2584, ambang %.16f (selisih ke manifest %.2g), tp/n_pred 2513/2549" % (t, t - ambang))
        ambang = t   # ambang tetap untuk semua konfigurasi = ambang turunan ulang (selisih ke manifest < 1e-9)
    M = {n: metrik(P, ph, ambang) for n, P in oof.items()}
    b = M["BASE"]
    print("n phishing = %d, n ham+spam = %d; ambang beku %.16f" % (ph.sum(), (~ph).sum(), ambang))
    print("%-14s %8s %8s %8s %8s %6s %5s" % ("konfigurasi", "PR-AUC", "dPR", "recall", "dRec", "salah", "dFP"))
    for n, (ap, rc, fp) in M.items():
        print("%-14s %8.4f %+8.4f %8.4f %+8.4f %6d %+5d" % (n, ap, ap - b[0], rc, rc - b[1], fp, fp - b[2]))
    for nama in ("JAUH", "PHISH", "GABUNG"):
        t_, a_ = M[nama], [M["%s_acak%d" % (nama, s)] for s in range(N_ACAK)]
        ap = b[0] - t_[0] >= 0.002 and b[0] - t_[0] > max(b[0] - a[0] for a in a_)
        rc = b[1] - t_[1] >= 0.02 and b[1] - t_[1] > max(b[1] - a[1] for a in a_)
        fp = t_[2] - b[2] >= 15 and t_[2] - b[2] > max(a[2] - b[2] for a in a_)
        print("%s berbeda dari acak? PR-AUC=%s recall=%s salah_tangkap=%s" % (nama, ap, rc, fp))


def main():
    df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False, usecols=["content_hash", "label", "body_text"])
    sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
    df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
    assert df["split"].notna().all(), "ada email tanpa indeks split"
    df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
    assert len(df) == 7438, len(df)
    ambang = json.loads(Path(MANIFEST).read_text(encoding="utf-8"))["ambang"]
    jalankan(df["body_text"].to_numpy(dtype=object), df["label"].to_numpy(), df["fold"].to_numpy(), ambang)


if __name__ == "__main__":
    main()