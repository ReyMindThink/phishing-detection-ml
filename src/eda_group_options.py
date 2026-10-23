"""Bandingkan 3 skenario pengelompokan split. Hanya angka agregat."""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ARTEFAK = {"spamassassin.taint.org"}
URUTAN = ["ham", "spam", "phishing"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["label", "sender_domain", "group_id"])
n = len(df)

# Domain generik = muncul di lebih dari satu kelas (data-driven) + artefak.
per_dom = df[df["sender_domain"] != ""].groupby("sender_domain")["label"].nunique()
generik = set(per_dom[per_dom > 1].index) | ARTEFAK
print("Domain generik/artefak dikecualikan:", len(generik))

# Domain yang layak jadi penghubung grup (selain itu = NaN = tidak dipakai).
dom_semua = df["sender_domain"].where(
    (df["sender_domain"] != "") & ~df["sender_domain"].isin(generik))
dom_hamspam = dom_semua.where(df["label"] != "phishing")


def tepi_bintang(kunci):
    """Hubungkan tiap baris ke baris pertama yang punya kunci sama."""
    pertama = pd.Series(np.arange(n)).groupby(kunci).transform("min")
    ok = pertama.notna().to_numpy()
    return np.arange(n)[ok], pertama[ok].astype(int).to_numpy()


def hitung_grup(daftar_kunci):
    r, c = [], []
    for kunci in daftar_kunci:
        a, b = tepi_bintang(kunci)
        r.append(a)
        c.append(b)
    r, c = np.concatenate(r), np.concatenate(c)
    G = coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
    return connected_components(G, directed=False)[1]


skenario = {
    "A (teks saja)": [df["group_id"]],
    "B (teks + domain semua kelas)": [df["group_id"], dom_semua],
    "C (teks + domain ham/spam saja)": [df["group_id"], dom_hamspam],
}

for nama, kunci in skenario.items():
    tmp = df.assign(g=hitung_grup(kunci))
    ukuran = tmp.groupby("g").size()
    campur = int((tmp.groupby("g")["label"].nunique() > 1).sum())
    print(f"\n=== {nama}: total grup={len(ukuran)}, grup campur label={campur} ===")
    for label in URUTAN:
        u = tmp[tmp["label"] == label].groupby("g").size()
        print(f"  {label:9} grup={len(u):5} terbesar={u.max():4} "
              f"({u.max() / u.sum() * 100:4.1f}% dari kelas)")

# --- Diagnosa grup terbesar + cek artefak ---
print("\nspamassassin.taint.org per kelas:",
      df[df["sender_domain"] == "spamassassin.taint.org"]["label"].value_counts().to_dict())


def diagnosa(nama, kunci, label):
    tmp = df.assign(g=hitung_grup(kunci))
    sub = tmp[tmp["label"] == label]
    g_besar = sub.groupby("g").size().idxmax()
    isi = tmp[tmp["g"] == g_besar]
    dom = isi["sender_domain"].replace("", "(kosong)")
    print(f"\n--- {nama}: grup terbesar {label} ---")
    print("email:", len(isi), "| domain unik:", dom.nunique(),
          "| grup teks asal:", isi["group_id"].nunique())
    print("5 domain teratas:")
    print(dom.value_counts().head(5).to_string())


diagnosa("C", skenario["C (teks + domain ham/spam saja)"], "ham")
diagnosa("B", skenario["B (teks + domain semua kelas)"], "phishing")