"""Tahap 6-2: tolok ukur subset sulit H2 (HTML tanpa header milis).
Latih di SEMUA train (OOF 5 lipatan), nilai baris H2. Test dibuang. Hanya angka agregat."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

SEED = 42
TOKEN = r"(?u)\b[a-zA-Z]{3,}\b"
BENTUK_NUM = ["has_html", "has_plain", "n_parts", "html_bytes", "plain_bytes", "n_headers",
              "n_received", "has_list_header", "has_mailman", "has_message_id", "has_x_mailer"]
BENTUK_CAT = ["content_type", "charset"]
LINK = ["n_links", "n_link_domains", "n_link_mismatch", "n_link_ip", "n_link_userinfo",
        "n_link_punycode", "max_url_len", "max_host_labels", "n_images", "n_forms"]
NUM = BENTUK_NUM + LINK

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "body_text"] + NUM + BENTUK_CAT)
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
df[NUM] = df[NUM].astype(float)
y = df["label"].to_numpy()
fold = df["fold"].to_numpy()
ph = y == "phishing"
H2 = ((df["has_html"] == 1) & (df["has_list_header"] == 0)).to_numpy()
n_h2 = {k: int((H2 & (y == k)).sum()) for k in ["ham", "spam", "phishing"]}
assert n_h2 == {"ham": 126, "spam": 729, "phishing": 2543}, n_h2
ham_ov = H2 & (y == "ham") & (df["n_headers"].to_numpy() >= 14)
assert ham_ov.sum() == 40, ham_ov.sum()
print("KONTROL OK: ukuran H2 =", n_h2, "| ham tumpang tindih (n_headers >= 14) =", int(ham_ov.sum()))
print("Acak PR-AUC phishing vs spam di H2 = %.3f" % (ph[H2 & (y != "ham")].mean()))


def skala():
    return Pipeline([("log", FunctionTransformer(np.log1p)), ("sc", StandardScaler())])


def onehot(padat):
    return OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20,
                         sparse_output=not padat)


def tfidf():
    return TfidfVectorizer(token_pattern=TOKEN, lowercase=True, min_df=3,
                           max_features=20000, sublinear_tf=True)


def hgb():
    return HistGradientBoostingClassifier(random_state=SEED)


def lr(n=2000):
    return LogisticRegression(max_iter=n, random_state=SEED)


MODEL = {
    "S bentuk (HGB)": lambda: Pipeline([("p", ColumnTransformer(
        [("n", "passthrough", BENTUK_NUM), ("c", onehot(True), BENTUK_CAT)])), ("m", hgb())]),
    "S bentuk (LogReg)": lambda: Pipeline([("p", ColumnTransformer(
        [("n", skala(), BENTUK_NUM), ("c", onehot(False), BENTUK_CAT)])), ("m", lr())]),
    "L link (HGB)": lambda: Pipeline([("p", ColumnTransformer(
        [("n", "passthrough", LINK)])), ("m", hgb())]),
    "T teks (LogReg)": lambda: Pipeline([("p", ColumnTransformer(
        [("t", tfidf(), "body_text")])), ("m", lr(1000))]),
    "T+L teks+link (LogReg)": lambda: Pipeline([("p", ColumnTransformer(
        [("t", tfidf(), "body_text"), ("n", skala(), LINK)])), ("m", lr())]),
    "S+T+L semua (LogReg)": lambda: Pipeline([("p", ColumnTransformer(
        [("t", tfidf(), "body_text"), ("n", skala(), NUM), ("c", onehot(False), BENTUK_CAT)])),
        ("m", lr())]),
}
KONTROL = {"S bentuk (HGB)": 0.995, "T teks (LogReg)": 0.994}


def oof(buat):
    p = np.zeros(len(df))
    for k in range(5):
        va = fold == k
        m = buat()
        m.fit(df.loc[~va], y[~va])
        p[va] = m.predict_proba(df.loc[va])[:, list(m.classes_).index("phishing")]
    return p


sp_mask = H2 & (y != "ham")
hasil, auc_lipatan = {}, {}
print("\n%-24s %9s | %-24s %8s | %s" % ("model", "PR-AUC ph", "H2 AUC ph-vs-spam (lipatan)",
                                       "PR-AUC", "kontrol"))
for nama, buat in MODEL.items():
    p = oof(buat)
    hasil[nama] = p
    pr_semua = average_precision_score(ph, p)
    per = [roc_auc_score(ph[sp_mask & (fold == k)], p[sp_mask & (fold == k)]) for k in range(5)]
    auc_lipatan[nama] = np.array(per)
    kon = ""
    if nama in KONTROL:
        kon = "%.3f -> %s" % (KONTROL[nama], "OK" if round(pr_semua, 3) == KONTROL[nama] else "GAGAL")
    print("%-24s %9.3f | %.3f (%.3f-%.3f)%s %8.3f | %s" % (
        nama, pr_semua, roc_auc_score(ph[sp_mask], p[sp_mask]), min(per), max(per), "",
        average_precision_score(ph[sp_mask], p[sp_mask]), kon))

print("\nSelisih AUC H2 per lipatan terhadap 'S bentuk (HGB)':")
dasar = auc_lipatan["S bentuk (HGB)"]
for nama in ["S bentuk (LogReg)", "T teks (LogReg)", "T+L teks+link (LogReg)", "S+T+L semua (LogReg)"]:
    d = auc_lipatan[nama] - dasar
    print("%-24s rata-rata=%+.4f  membaik di %d dari 5 lipatan" % (nama, d.mean(), (d > 0).sum()))
d = auc_lipatan["T+L teks+link (LogReg)"] - auc_lipatan["T teks (LogReg)"]
print("%-24s rata-rata=%+.4f  membaik di %d dari 5 lipatan (T+L vs T)" % ("", d.mean(), (d > 0).sum()))

print("\n=== Ambang: recall phishing 90% di OOF seluruh train; hitungan di H2 ===")
print("%-24s %9s | %s | %s | %s | %s" % ("model", "ambang", "recall ph H2", "spam ditandai",
                                          "ham ditandai", "ham-tumpang ditandai"))
for nama, p in hasil.items():
    t = np.quantile(p[ph], 0.10)
    f = p >= t
    print("%-24s %9.4f | %5d/%d      | %5d/%d      | %3d/%d      | %2d/%d" % (
        nama, t, (f & H2 & ph).sum(), n_h2["phishing"], (f & H2 & (y == "spam")).sum(),
        n_h2["spam"], (f & H2 & (y == "ham")).sum(), n_h2["ham"], (f & ham_ov).sum(),
        int(ham_ov.sum())))