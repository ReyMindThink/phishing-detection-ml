"""Tahap 6-3: ablasi kata sumber (jejak ham) pada model teks. Train + 5 lipatan (splits.csv).
Test dibuang. Hanya kata dan angka agregat."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]
TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
W1 = ["listinfo", "mailman", "wrote", "list", "spamassassin", "razor", "newsisfree",
      "xent", "freshrpms", "rpm", "fork", "linux", "supplied"]
W2 = W1 + ["gnupg", "pgp"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "has_html", "has_list_header", "body_text"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
for c in ["has_html", "has_list_header"]:
    df[c] = df[c].astype(str) == "True"
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
sub = df["subset"].to_numpy()
ph = y == "phishing"
H2 = (df["has_html"] & ~df["has_list_header"]).to_numpy()
spam_h2 = H2 & (y != "ham")

kosa = CountVectorizer(token_pattern=TOKEN, lowercase=True, min_df=100).fit(df["body_text"])
kandidat = [w for w in kosa.get_feature_names_out() if w not in set(W2)]
ACAK = sorted(np.random.RandomState(42).choice(kandidat, size=len(W2), replace=False).tolist())
print("W1 (%d kata): %s" % (len(W1), " ".join(W1)))
print("W2 = W1 + gnupg pgp (%d kata)" % len(W2))
print("ACAK (kontrol, %d kata dari kosakata berfrekuensi tinggi): %s\n" % (len(ACAK), " ".join(ACAK)))


def oof(stop):
    P = np.zeros((len(df), 3))
    for k in range(5):
        va = fold == k
        m = Pipeline([("tfidf", TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3,
                                                max_features=20000, sublinear_tf=True,
                                                stop_words=stop)),
                      ("clf", LogisticRegression(max_iter=1000, random_state=42))])
        m.fit(df.loc[~va, "body_text"], y[~va])
        urut = [list(m.classes_).index(c) for c in URUTAN]
        P[va] = m.predict_proba(df.loc[va, "body_text"])[:, urut]
    return P


VARIAN = {"baseline": None, "W1": W1, "W2": W2, "acak": ACAK}
ringkas, ham_sub, ph_file = {}, {}, {}
for nama, stop in VARIAN.items():
    P = oof(stop)
    pred = np.array(URUTAN)[P.argmax(axis=1)]
    p = P[:, 2]
    if nama == "baseline":
        diag = [int((pred[y == c] == c).sum()) for c in URUTAN]
        assert diag == [3245, 1317, 2584], diag
        print("KONTROL OK: diagonal baseline = ham 3245, spam 1317, phishing 2584 (sama dengan 5d-2)\n")
    per = [roc_auc_score(ph[spam_h2 & (fold == k)], p[spam_h2 & (fold == k)]) for k in range(5)]
    t = np.quantile(p[ph], 0.10)
    ringkas[nama] = {
        "macroF1": f1_score(y, pred, average="macro"),
        "PR-AUC ph": average_precision_score(ph, p),
        "AUC H2": roc_auc_score(ph[spam_h2], p[spam_h2]),
        "AUC H2 min": min(per),
        "rec ham": (pred[y == "ham"] == "ham").mean(),
        "rec spam": (pred[y == "spam"] == "spam").mean(),
        "rec ph": (pred[ph] == "phishing").mean(),
        "ham H2 ditandai": int(((p >= t) & H2 & (y == "ham")).sum()),
    }
    ham_sub[nama] = {s: (pred[sub == s] == "ham").mean() for s in ["easy_ham", "easy_ham_2", "hard_ham"]}
    ph_file[nama] = {s: (pred[sub == s] == "phishing").mean() for s in sorted(set(sub[ph]))}

print("=== Ringkasan (OOF seluruh train; ham H2 ditandai dari 126 pada ambang recall phishing 90%) ===")
print(pd.DataFrame(ringkas).round(3).to_string())
print("\n=== Recall ham per subset (tebakan terbanyak) ===")
print(pd.DataFrame(ham_sub).round(3).to_string())
print("\n=== Recall phishing per file ===")
print(pd.DataFrame(ph_file).round(3).to_string())