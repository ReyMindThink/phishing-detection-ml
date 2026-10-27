"""Tahap 8-3a: bekukan model akhir (opsi B: rata-rata 5 model lipatan, teks saja, LogReg C=1).
Latih 5 model di data TRAIN, simpan ke models/ (diabaikan Git), tulis docs/model_manifest.json
(SHA256 tiap model, ambang eksak, versi library). Test tidak disentuh. Jalankan: python -m src.freeze_model"""
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline

from src.frozen_model import MANIFEST, URUTAN, muat_ensemble, sha256_file

TARGET = 0.93

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
ph = y == "phishing"
teks = df["body_text"]

Path("models").mkdir(exist_ok=True)
oof = np.zeros((len(df), 3))
info = []
for k in range(5):
    va = fold == k
    model = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                  min_df=3, max_features=20000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(teks[~va], y[~va])
    urut = [list(model.classes_).index(c) for c in URUTAN]
    oof[va] = model.predict_proba(teks[va])[:, urut]
    path = "models/fold%d.joblib" % k
    joblib.dump(model, path)
    info.append({"path": path, "sha256": sha256_file(path), "n_latih": int((~va).sum())})

# KONTROL: model yang disimpan harus mereproduksi OOF 7-1 dan ambang resmi
cm = confusion_matrix(y, np.array(URUTAN)[oof.argmax(axis=1)], labels=URUTAN)
assert np.diag(cm).tolist() == [3245, 1317, 2584], np.diag(cm).tolist()
t = float(np.sort(oof[ph, 2])[::-1][int(np.ceil(TARGET * ph.sum())) - 1])
tp, n_pred = int(((oof[:, 2] >= t) & ph).sum()), int((oof[:, 2] >= t).sum())
assert round(t, 4) == 0.5040 and (tp, n_pred) == (2513, 2549), (t, tp, n_pred)
print("KONTROL OK: OOF 3245/1317/2584, ambang eksak %r, 2513/2549" % t)

manifest = {
    "tahap": "8-3a",
    "model": "TF-IDF body_text (token huruf >= 3, min_df 3, 20000 fitur, sublinear_tf) + LogReg C=1, seed 42; teks saja",
    "aturan": "rata-rata P dari 5 model lipatan; phishing bila P(phishing) >= ambang, selain itu ham/spam = argmax rata-rata",
    "target_recall_oof": TARGET,
    "ambang": t,
    "sha256_id_train": hashlib.sha256("\n".join(sorted(df["content_hash"])).encode()).hexdigest(),
    "versi": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
              "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
    "models": info,
}
Path(MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# VERIFIKASI: muat ulang LEWAT jalur terverifikasi dan bandingkan dengan prediksi saat dilatih
models, _ = muat_ensemble()
for k, m in enumerate(models):
    va = fold == k
    urut = [list(m.classes_).index(c) for c in URUTAN]
    assert np.allclose(m.predict_proba(teks[va])[:, urut], oof[va]), "model %d berbeda" % k
print("VERIFIKASI MUAT OK: 5 model dimuat setelah SHA256 cocok dan mereproduksi OOF")
print("Ambang eksak: %r | berkas:" % t, [(i["path"], i["sha256"][:12]) for i in info])