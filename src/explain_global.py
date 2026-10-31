"""Tahap 9-1: penjelasan global model beku (5 model lipatan, teks saja; data TRAIN saja).
KONTROL: (a) uraian manual logit phishing = decision_function; (b) SHAP linear = koefisien x (x - rata-rata).
Hanya agregat dan token huruf yang dicetak (tanpa isi email). Jalankan: python -m src.explain_global"""
import numpy as np
import pandas as pd

from src.frozen_model import muat_ensemble

N_UJI, N_LATAR, TOP = 200, 500, 20


def bagian(model):
    vec, clf = model.named_steps["tfidf"], model.named_steps["clf"]
    return vec, clf, list(clf.classes_)


def kontrol_manual(model, teks_uji):
    vec, clf, kls = bagian(model)
    ip = kls.index("phishing")
    X = vec.transform(teks_uji)
    manual = X @ clf.coef_[ip] + clf.intercept_[ip]
    assert np.allclose(manual, clf.decision_function(X)[:, ip]), "kontrol (a) gagal"
    return X


def kontrol_shap(model, X_uji, teks_latar):
    import shap
    vec, clf, kls = bagian(model)
    ip = kls.index("phishing")
    bg, Xd = vec.transform(teks_latar).toarray(), X_uji.toarray()
    masker = shap.maskers.Independent(bg, max_samples=N_LATAR)   # tanpa subsampling diam-diam
    sv = shap.LinearExplainer(clf, masker).shap_values(Xd)
    print("bentuk keluaran SHAP:", type(sv).__name__, getattr(sv, "shape", None))
    if isinstance(sv, list):
        sv = sv[ip]
    elif sv.ndim == 3:
        sv = sv[:, :, ip] if sv.shape[-1] == len(kls) else sv[ip]
    assert sv.shape == Xd.shape, sv.shape
    ref = clf.coef_[ip] * (Xd - bg.mean(axis=0))
    print("selisih maks |SHAP - rumus|: %.3g" % np.abs(sv - ref).max())
    assert np.allclose(sv, ref, atol=1e-6), "kontrol (b) gagal"


def konsistensi(models):
    tabel = []
    for m in models:
        vec, clf, kls = bagian(m)
        tabel.append(pd.DataFrame({k: clf.coef_[kls.index(k)] for k in ("phishing", "ham", "spam")},
                                  index=vec.get_feature_names_out()))
    bersama = sorted(set.intersection(*[set(t.index) for t in tabel]))
    ambil = lambda k: np.column_stack([t.loc[bersama, k].to_numpy() for t in tabel])
    P, H, S = ambil("phishing"), ambil("ham"), ambil("spam")
    ukuran = [len(t) for t in tabel]
    ok = (P[:, 0] != 0) & (np.sign(P) == np.sign(P[:, [0]])).all(axis=1)
    print("Ukuran kosakata per model:", ukuran)
    print("Kata di kelima kosakata: %d = %.1f%% dari rata-rata ukuran" % (len(bersama), 100 * len(bersama) / np.mean(ukuran)))
    print("Tanda koefisien phishing sama di 5 model: %d dari %d kata bersama (%.1f%%)" % (ok.sum(), len(bersama), 100 * ok.mean()))
    kata, rata = np.array(bersama), P.mean(axis=1)
    lain = np.where(H.mean(axis=1) >= S.mean(axis=1), "ham", "spam")
    idx = np.flatnonzero(ok)
    idx = idx[np.argsort(rata[idx])]
    for judul, pilih in (("Pendorong PHISHING (koefisien rata-rata terbesar)", idx[::-1][:TOP]),
                         ("Pendorong MENJAUHI phishing (kelas lain yang lebih besar)", idx[:TOP])):
        print(judul)
        for i in pilih:
            print("  %-16s %+.3f  (min %+.3f, maks %+.3f) lain=%s" % (kata[i], rata[i], P[i].min(), P[i].max(), lain[i]))


def main():
    df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False, usecols=["content_hash", "body_text"])
    sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
    df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
    assert df["split"].notna().all(), "ada email tanpa indeks split"
    df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
    assert len(df) == 7438, len(df)
    models, _ = muat_ensemble()
    teks, fold = df["body_text"], df["fold"].to_numpy()
    uji = teks.iloc[np.flatnonzero(fold == 0)[:N_UJI]]
    latar = teks.iloc[np.flatnonzero(fold != 0)[:N_LATAR]]
    X = kontrol_manual(models[0], uji)
    print("KONTROL (a) OK: uraian manual = decision_function (n=%d)" % X.shape[0])
    kontrol_shap(models[0], X, latar)
    print("KONTROL (b) OK: SHAP = koefisien x (x - rata-rata latar); latar n=%d" % len(latar))
    konsistensi(models)


if __name__ == "__main__":
    main()