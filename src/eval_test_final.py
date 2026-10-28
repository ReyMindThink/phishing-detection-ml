"""Tahap 8-5: evaluasi test set SEKALI pada model beku (ambang eksak; tanpa penyetelan ulang apa pun).

Hanya angka agregat. Aturan, prediksi, dan pembacaan dikunci di docs/experiment_design.md dan dikomit
SEBELUM skrip ini dijalankan. Berhenti bila data/processed/test_proba.csv sudah ada (tanda sudah dijalankan).
Jalankan SEKALI: python -m src.eval_test_final
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score

from src.frozen_model import URUTAN, muat_ensemble, proba_ensemble, putusan

KONTROL = os.environ.get("UJI_ALUR_SINTETIS") != "1"    # "1" HANYA untuk menguji alur pada data sintetis
OUT = Path("data/processed/test_proba.csv")
JEMBATAN = {"barrera.org", "evergo.net", "pobox.com", "mithral.com", "slack.net"}    # sama dengan make_splits.py
ARTEFAK = {"spamassassin.taint.org"}
if OUT.exists():
    raise SystemExit("Evaluasi test SUDAH dijalankan (%s ada). Jangan diulang." % OUT)


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def bagian(judul):
    """Satu bagian diagnostik; kegagalannya tidak menghentikan bagian lain atau menghapus metrik inti."""
    def jalankan(f):
        print("\n=== %s ===" % judul)
        try:
            f()
        except Exception as e:
            print("GAGAL (bagian ini saja; metrik inti sudah tercetak dan tersimpan): %r" % (e,))
    return jalankan


df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "body_text", "sender_domain", "source_file"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "group_final", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
tr = df[df["split"] == "train"].reset_index(drop=True)
te = df[df["split"] == "test"].reset_index(drop=True)
if KONTROL:
    assert len(tr) == 7438 and len(te) == 1860, (len(tr), len(te))
    assert te["label"].value_counts().to_dict() == {"ham": 822, "spam": 362, "phishing": 676}

models, manifest = muat_ensemble()
t = manifest["ambang"]
ytr, fold = tr["label"].to_numpy(), tr["fold"].to_numpy()
oof = np.zeros((len(tr), 3))
for k, m in enumerate(models):
    va = fold == k
    urut = [list(m.classes_).index(c) for c in URUTAN]
    oof[va] = m.predict_proba(tr["body_text"][va])[:, urut]
if KONTROL:
    cm0 = confusion_matrix(ytr, np.array(URUTAN)[oof.argmax(axis=1)], labels=URUTAN)
    assert np.diag(cm0).tolist() == [3245, 1317, 2584], np.diag(cm0).tolist()
    tanda = oof[:, 2] >= t
    assert (int((tanda & (ytr == "phishing")).sum()), int(tanda.sum())) == (2513, 2549)
    print("KONTROL OK: OOF 3245/1317/2584 dan 2513/2549")

y = te["label"].to_numpy()
proba = proba_ensemble(models, te["body_text"])
pred = putusan(proba, t)
pp = proba[:, 2]
fish, flag = y == "phishing", pred == "phishing"
tp, n_flag, n_fish = int((flag & fish).sum()), int(flag.sum()), int(fish.sum())
R, P = tp / n_fish, tp / n_flag
print("\n=== METRIK INTI: test n=%d, ambang eksak %r ===" % (len(te), t))
print("Phishing: recall %.4f (%d/%d; Wilson 95%% %.3f-%.3f) | precision %.4f (%d/%d; Wilson 95%% %.3f-%.3f)" % (
    R, tp, n_fish, *wilson(tp, n_fish), P, tp, n_flag, *wilson(tp, n_flag)))
pr_, rc_, f1_, sup_ = precision_recall_fscore_support(y, pred, labels=URUTAN, zero_division=0)
for i, c in enumerate(URUTAN):
    print("  %-9s precision %.4f | recall %.4f | F1 %.4f | n=%d" % (c, pr_[i], rc_[i], f1_[i], sup_[i]))
cm = confusion_matrix(y, pred, labels=URUTAN)
print("Macro-F1 %.4f | akurasi %.4f | ROC-AUC phishing-vs-sisa %.4f | PR-AUC phishing %.4f (acak %.3f)" % (
    f1_.mean(), np.trace(cm) / len(te), roc_auc_score(fish, pp), average_precision_score(fish, pp), fish.mean()))
print("Confusion (baris = benar, kolom = putusan; urutan %s):" % URUTAN)
print(pd.DataFrame(cm, index=URUTAN, columns=URUTAN).to_string())
print("Target recall >= 0,90 (estimasi titik): %s | prediksi terkunci recall 0,89-0,95: %s | precision 0,96-0,99: %s" % (
    "TERPENUHI" if R >= 0.90 else "TIDAK terpenuhi", "dalam" if 0.89 <= R <= 0.95 else "DI LUAR",
    "dalam" if 0.96 <= P <= 0.99 else "DI LUAR"))
pd.DataFrame({"content_hash": te["content_hash"], "label": y, "group_final": te["group_final"],
              "p_ham": proba[:, 0], "p_spam": proba[:, 1], "p_phishing": pp, "putusan": pred}).to_csv(OUT, index=False)
print("Prediksi test disimpan di %s (diabaikan Git) untuk 8-6; evaluasi TIDAK diulang." % OUT)


@bagian("Analisis ambang (deskriptif; ambang TIDAK disetel ulang)")
def _():
    for th in (0.2, 0.3, 0.4, 0.45, t, 0.55, 0.6, 0.7, 0.8, 0.9):
        f = pp >= th
        print("  ambang %.4f: recall %.4f | precision %.4f | ditandai ham %d, spam %d" % (
            th, (f & fish).sum() / n_fish, (f & fish).sum() / max(f.sum(), 1), (f & (y == "ham")).sum(), (f & (y == "spam")).sum()))


@bagian("Kalibrasi P(phishing) (bin lebar 0,1; * bila n < 30; tidak dikalibrasi ulang)")
def _():
    b = np.minimum((pp * 10).astype(int), 9)
    for i in range(10):
        m = b == i
        if m.sum():
            print("  [%.1f-%.1f] n=%-4d%s rata-rata P %.3f | tingkat phishing sebenarnya %.3f" % (
                i / 10, (i + 1) / 10, m.sum(), "*" if m.sum() < 30 else " ", pp[m].mean(), fish[m].mean()))
    print("  Brier (phishing vs sisa): %.4f" % np.mean((pp - fish) ** 2))


@bagian("Recall phishing per email, per grup, per file Nazario")
def _():
    g = te["group_final"].to_numpy()[fish]
    pg = pd.Series(flag[fish]).groupby(g).mean()
    print("  per email %.4f | per grup (bobot sama) %.4f; %d grup; grup terbesar %d email" % (
        R, pg.mean(), len(pg), pd.Series(g).value_counts().iloc[0]))
    for f_ in sorted(set(te["source_file"][fish])):
        m = fish & (te["source_file"].to_numpy() == f_)
        print("  %-16s n=%-4d%s recall %.3f" % (f_, m.sum(), "*" if m.sum() < 30 else " ", flag[m].mean()))


@bagian("Domain pengirim: tumpang tindih phishing train-test (dua penyebut) dan ketepatan menurut domain")
def _():
    per_dom = df[df["sender_domain"] != ""].groupby("sender_domain")["label"].nunique()
    dikecualikan = set(per_dom[per_dom > 1].index) | ARTEFAK | JEMBATAN
    d = te[fish & (te["sender_domain"] != "").to_numpy()]
    sudah = d["sender_domain"].isin(set(tr[tr["label"] == "phishing"]["sender_domain"]))
    layak = ~d["sender_domain"].isin(dikecualikan)
    print("  email phishing test berdomain %d | domain ada di train phishing: %d (%.1f%%) | domain layak: %d, di antaranya ada di train: %d (%.1f%%)" % (
        len(d), sudah.sum(), 100 * sudah.mean(), layak.sum(), (sudah & layak).sum(), 100 * (sudah & layak).sum() / max(int(layak.sum()), 1)))
    dom_train = set(tr["sender_domain"]) - {""}
    for c in URUTAN:
        for nama, m in (("tanpa domain", te["sender_domain"].to_numpy() == ""),
                        ("domain ADA di train", te["sender_domain"].isin(dom_train).to_numpy()),
                        ("domain TIDAK ada di train", (~te["sender_domain"].isin(dom_train) & (te["sender_domain"] != "")).to_numpy())):
            mm = (y == c) & m
            if mm.sum():
                print("  %-9s %-26s n=%-4d%s putusan benar %.3f" % (c, nama, mm.sum(), "*" if mm.sum() < 30 else " ", (pred[mm] == c).mean()))


@bagian("Kemiripan test-train (cosine maks ke train; TF-IDF dilatih di body_text train)")
def _():
    vec = TfidfVectorizer(min_df=2, sublinear_tf=True, max_features=50000)
    Xtr = vec.fit_transform(tr["body_text"])
    maks = (vec.transform(te["body_text"]) @ Xtr.T.tocsc()).toarray().max(axis=1)
    for c in URUTAN:
        m = y == c
        print("  %-9s n=%-4d median %.3f | persentil 90 %.3f | 99 %.3f | maks %.3f | >=0.9: %d | >=0.8: %d | >=0.7: %d" % (
            c, m.sum(), np.median(maks[m]), *np.quantile(maks[m], [0.9, 0.99]), maks[m].max(),
            (maks[m] >= 0.9).sum(), (maks[m] >= 0.8).sum(), (maks[m] >= 0.7).sum()))
    kel = np.digitize(maks, [0.5, 0.7])
    for i, nama in enumerate(("< 0.5", "0.5-0.7", ">= 0.7")):
        m = fish & (kel == i)
        if m.sum():
            print("  recall phishing, kemiripan %-8s n=%-4d%s %.3f" % (nama, m.sum(), "*" if m.sum() < 30 else " ", flag[m].mean()))


@bagian("Recall per model lipatan tunggal pada ambang eksak (eksploratif; ambang tidak setara antar model)")
def _():
    for k, m_ in enumerate(models):
        urut = [list(m_.classes_).index(c) for c in URUTAN]
        f = m_.predict_proba(te["body_text"])[:, urut][:, 2] >= t
        print("  lipatan %d: recall %.4f | ditandai %d | precision %.4f" % (
            k, (f & fish).sum() / n_fish, f.sum(), (f & fish).sum() / max(f.sum(), 1)))


@bagian("Precision pada prevalensi lain (indikatif; FPR dari ham+spam SpamAssassin 2003)")
def _():
    neg = ~fish
    fp = int((flag & neg).sum())
    fpr, fpr_hi = fp / neg.sum(), wilson(fp, int(neg.sum()))[1]
    print("  FPR test %.4f (%d/%d), batas atas Wilson %.4f" % (fpr, fp, neg.sum(), fpr_hi))
    for pi in (0.001, 0.01, 0.05, fish.mean()):
        print("  prevalensi phishing %.3f: precision %.4f (FPR titik) | %.4f (FPR batas atas)" % (
            pi, R * pi / (R * pi + fpr * (1 - pi)), R * pi / (R * pi + fpr_hi * (1 - pi))))