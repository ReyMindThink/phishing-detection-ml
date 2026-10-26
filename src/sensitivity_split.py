"""Tahap 8-1: uji kepekaan split (ambang cosine, batas grup terbesar, jumlah domain jembatan).
Model hanya dilatih dan dinilai di data TRAIN. Teks test hanya ikut membangun graf grup
(seperti produksi, tanpa label/model). splits.csv TIDAK diubah. Hanya angka agregat."""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline

URUTAN = ["ham", "spam", "phishing"]
ARTEFAK = {"spamassassin.taint.org"}
JEMBATAN = {"barrera.org", "evergo.net", "pobox.com", "mithral.com", "slack.net"}

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subject", "body_text", "sender_domain", "group_id"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "group_final", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
n = len(df)
assert df["split"].notna().all() and n == 9298, n
y_all = df["label"].to_numpy()
tr = np.where(df["split"] == "train")[0]
assert len(tr) == 7438, len(tr)
y = y_all[tr]
ph = y == "phishing"
teks = df["body_text"].iloc[tr].reset_index(drop=True)
fold_resmi = df["fold"].to_numpy()[tr]

# --- graf kemiripan teks (sama dengan make_clean_dataset.py), simpan semua pasangan >= 0,7 ---
X = TfidfVectorizer(min_df=2, sublinear_tf=True, max_features=50000).fit_transform(
    (df["subject"] + " " + df["body_text"]).tolist())
R, C, V = [], [], []
for mulai in range(0, n, 1000):
    S = (X[mulai:mulai + 1000] @ X.T).toarray()
    r, c = np.nonzero(S >= 0.7)
    R.append(r + mulai)
    C.append(c)
    V.append(S[r, c])
R, C, V = np.concatenate(R), np.concatenate(C), np.concatenate(V)


def komponen(r, c):
    G = coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
    return connected_components(G, directed=False)[1]


def grup_teks(ambang):
    m = V >= ambang
    return komponen(R[m], C[m])


def sama_partisi(a, b):
    return len(set(zip(a, b))) == len(set(a)) == len(set(b))


per_dom = df[df["sender_domain"] != ""].groupby("sender_domain")["label"].nunique()
generik = set(per_dom[per_dom > 1].index) | ARTEFAK


def tepi_bintang(kunci):
    pertama = pd.Series(np.arange(n)).groupby(kunci).transform("min")
    ok = pertama.notna().to_numpy()
    return np.arange(n)[ok], pertama[ok].astype(int).to_numpy()


def grup_final(g_teks, buang):
    """Grup teks + domain ham/spam; domain generik dan 'buang' (jembatan) diabaikan."""
    dom = df["sender_domain"].where((df["sender_domain"] != "")
                                    & ~df["sender_domain"].isin(generik | set(buang))
                                    & (df["label"] != "phishing"))
    r, c = [], []
    for kunci in (pd.Series(g_teks), dom):
        a, b = tepi_bintang(kunci)
        r.append(a)
        c.append(b)
    return komponen(np.concatenate(r), np.concatenate(c))


def lipatan(g_tr, seed):
    f = np.full(len(g_tr), -1)
    for k, (_, va) in enumerate(StratifiedGroupKFold(5, shuffle=True, random_state=seed)
                                .split(np.arange(len(g_tr)), y, g_tr)):
        f[va] = k
    return f


# --- KONTROL 1: graf dan grup produksi terproduksi ulang persis ---
g09 = df["group_id"].to_numpy()
assert sama_partisi(grup_teks(0.9), g09), "grup cosine 0,9 tidak sama dengan group_id"
gf_resmi = df["group_final"].to_numpy()
assert sama_partisi(grup_final(g09, JEMBATAN), gf_resmi), "group_final tidak sama"
assert (lipatan(gf_resmi[tr], 42) == fold_resmi).all(), "lipatan tidak sama"
print("KONTROL 1 OK: group_id (cosine 0,9), group_final, dan lipatan resmi terproduksi ulang")

# --- jalur jembatan (greedy seperti eda_group_hubs.py): buang domain dengan tetangga terbanyak ---
ham_mask = y_all == "ham"
ham = df[ham_mask & (df["sender_domain"] != "") & ~df["sender_domain"].isin(generik)]
tetangga = {}
for ds in ham.groupby("group_id")["sender_domain"].agg(lambda s: sorted(set(s))):
    if len(ds) > 1:
        for d in ds:
            tetangga.setdefault(d, set()).update(x for x in ds if x != d)
buang, jalur = [], {}
for langkah in range(16):
    g = grup_final(g09, buang)
    ukuran = pd.Series(g[ham_mask]).value_counts()
    for T in (0.10, 0.05, 0.02):
        if ukuran.iloc[0] / ham_mask.sum() < T and T not in jalur:
            jalur[T] = list(buang)
    if 0.02 in jalur:
        break
    kandidat = [d for d in df.loc[g == ukuran.index[0], "sender_domain"].unique()
                if d in tetangga and d not in buang]
    if not kandidat:
        break
    buang.append(max(kandidat, key=lambda x: len(tetangga[x])))
for T in (0.10, 0.05, 0.02):
    jalur.setdefault(T, list(buang))
assert set(jalur[0.05]) == JEMBATAN, jalur[0.05]
print("KONTROL 2 OK: jalur greedy batas 5%% = 5 jembatan resmi | jumlah jembatan batas 10%%/5%%/2%%: "
      "%d/%d/%d" % (len(jalur[0.10]), len(jalur[0.05]), len(jalur[0.02])))


def oof_teks(f):
    oof = np.zeros((len(tr), 3))
    for k in range(5):
        va = f == k
        model = Pipeline([
            ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b[a-zA-Z]{3,}\b", lowercase=True,
                                      min_df=3, max_features=20000, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ])
        model.fit(teks[~va], y[~va])
        urut = [list(model.classes_).index(c) for c in URUTAN]
        oof[va] = model.predict_proba(teks[va])[:, urut]
    return oof


def jalankan(nama, g_full, f):
    g = g_full[tr]
    oof = oof_teks(f)
    p = oof[:, 2]
    t = np.sort(p[ph])[::-1][int(np.ceil(0.93 * ph.sum())) - 1]
    tp, n_pred = int(((p >= t) & ph).sum()), int((p >= t).sum())
    besar = [pd.Series(g[y == c]).value_counts().iloc[0] / (y == c).sum() * 100 for c in URUTAN]
    mf1 = f1_score(y, np.array(URUTAN)[oof.argmax(axis=1)], average="macro")
    h = dict(nama=nama, pr=average_precision_score(ph, p), mf1=mf1, t=t, prec=tp / n_pred,
             tp=tp, n_pred=n_pred, ngrup=len(np.unique(g)), besar=besar, flag=max(besar) > 15,
             lip=(int(np.bincount(f).min()), int(np.bincount(f).max())), oof=oof)
    return h


hasil = [jalankan("S0 resmi (kontrol)", gf_resmi, fold_resmi)]
oof0 = hasil[0].pop("oof")
cm = confusion_matrix(y, np.array(URUTAN)[oof0.argmax(axis=1)], labels=URUTAN)
assert np.diag(cm).tolist() == [3245, 1317, 2584] and round(hasil[0]["t"], 4) == 0.5040
assert hasil[0]["tp"] == 2513 and hasil[0]["n_pred"] == 2549
print("KONTROL 3 OK: S0 mereproduksi OOF 7-1 (3245/1317/2584, ambang 0,5040, 2513/2549)")

skenario = [("R1 resmi, seed lipatan 43", gf_resmi, 43), ("R2 resmi, seed lipatan 44", gf_resmi, 44),
            ("C08 cosine 0,8", grup_final(grup_teks(0.8), sorted(JEMBATAN)), 42),
            ("C07 cosine 0,7", grup_final(grup_teks(0.7), sorted(JEMBATAN)), 42),
            ("J10 batas grup 10%", grup_final(g09, jalur[0.10]), 42),
            ("J02 batas grup 2%", grup_final(g09, jalur[0.02]), 42)]
for nama, g_full, seed in skenario:
    try:
        h = jalankan(nama, g_full, lipatan(g_full[tr], seed))
    except ValueError as e:        # mis. grup raksasa: ada lipatan tanpa satu kelas
        print("%s: GAGAL membentuk lipatan/model (%s)" % (nama, str(e)[:80]))
        continue
    h.pop("oof")
    hasil.append(h)

print("\nskenario | grup train | grup terbesar % ham/spam/phishing | n per lipatan | PR-AUC | "
      "macro-F1 | ambang | precision@recall0,93 | dPR | dPrec")
for h in hasil:
    print("%s | %d | %.1f/%.1f/%.1f%s | %d-%d | %.4f | %.3f | %.4f | %.3f (%d/%d) | %+.4f | %+.4f" % (
        h["nama"], h["ngrup"], *h["besar"], " (GRUP BESAR)" if h["flag"] else "", *h["lip"],
        h["pr"], h["mf1"], h["t"], h["prec"], h["tp"], h["n_pred"],
        h["pr"] - hasil[0]["pr"], h["prec"] - hasil[0]["prec"]))

# --- ATURAN (terkunci): noise = selisih terbesar antar-seed lipatan; peka bila |d| >= max(0,005; 2 x noise) ---
noise_pr = max(abs(h["pr"] - hasil[0]["pr"]) for h in hasil[1:3])
noise_pc = max(abs(h["prec"] - hasil[0]["prec"]) for h in hasil[1:3])
b_pr, b_pc = max(0.005, 2 * noise_pr), max(0.005, 2 * noise_pc)
print("\nNoise lipatan: PR-AUC %.4f, precision %.4f | batas peka: %.4f / %.4f" % (
    noise_pr, noise_pc, b_pr, b_pc))
for h in hasil[3:]:
    peka = abs(h["pr"] - hasil[0]["pr"]) >= b_pr or abs(h["prec"] - hasil[0]["prec"]) >= b_pc
    print("%s: %s%s" % (h["nama"], "PEKA" if peka else "tidak peka",
                        " (grup besar: hanya dilaporkan, tidak ditafsirkan)" if h["flag"] else ""))