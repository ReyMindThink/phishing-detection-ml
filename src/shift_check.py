"""Tahap 8-0: cek pergeseran skala ambang (model 60% vs 80% data latih, ambang tetap).
Hanya data train. Test dibuang di awal. Hanya angka agregat."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "body_text"])
sp = pd.read_csv("data/processed/splits.csv",
                 usecols=["content_hash", "group_final", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
ph = y == "phishing"
teks = df["body_text"]


def latih_prediksi(pakai, uji):
    """Latih di lipatan 'pakai'; kembalikan proba (ham, spam, phishing) untuk baris 'uji'."""
    tr = np.isin(fold, pakai)
    model = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                  min_df=3, max_features=20000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(teks[tr], y[tr])
    urut = [list(model.classes_).index(c) for c in URUTAN]
    return model.predict_proba(teks[uji])[:, urut]


# 80% (4 dari 5 lipatan) = OOF 7-1; dari sini ambang dihitung
oof = np.zeros((len(df), 3))
for k in range(5):
    oof[fold == k] = latih_prediksi([f for f in range(5) if f != k], fold == k)

# KONTROL: harus mereproduksi 5d-2 dan ambang 7-1 sebelum hasil baru dipercaya
cm = confusion_matrix(y, np.array(URUTAN)[oof.argmax(axis=1)], labels=URUTAN)
assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
p80 = oof[:, 2]
t = np.sort(p80[ph])[::-1][int(np.ceil(0.93 * ph.sum())) - 1]
assert round(t, 4) == 0.5040, t
assert int(((p80 >= t) & ph).sum()) == 2513
print("KONTROL OK: diagonal 3245/1317/2584, ambang %.4f, tp 2513" % t)


def lapor(nama, p):
    pred = p >= t
    tp = int((pred & ph).sum())
    n_pred = int(pred.sum())
    per_lip = [pred[ph & (fold == k)].mean() for k in range(5)]
    print("%s | recall %.3f | precision %.3f (%d/%d) | per lipatan %.3f-%.3f | "
          "median P pada phishing %.3f" % (nama, tp / ph.sum(), tp / n_pred, tp, n_pred,
                                           min(per_lip), max(per_lip), np.median(p[ph])))
    return tp / ph.sum()


print("\nAmbang tetap, kelas phishing n=%d" % ph.sum())
r80 = lapor("80%", p80)
r60 = []
for j in range(1, 5):                      # 4 putaran: buang satu lipatan latih tambahan
    p60 = np.zeros(len(df))
    for k in range(5):
        va = fold == k
        pakai = [f for f in range(5) if f not in (k, (k + j) % 5)]
        p60[va] = latih_prediksi(pakai, va)[:, 2]
    r60.append(lapor("60%% (putaran %d)" % j, p60))

selisih = r80 - float(np.mean(r60))
print("\nSelisih recall 80%% - rata-rata 60%%: %+.3f (rentang 60%%: %.3f-%.3f)"
      % (selisih, min(r60), max(r60)))
print("ATURAN (|selisih| <= 0.02 -> A, lebih -> B): %s" % ("A" if abs(selisih) <= 0.02 else "B"))