"""Tahap 11-1: ukur panjang body_text di data TRAIN (hanya angka agregat) untuk menentukan batas ukuran input."""
import pandas as pd

N_TRAIN = 7438
JUMLAH_LABEL = {"ham": 3288, "spam": 1448, "phishing": 2702}
BATAS = [20000, 50000, 100000, 250000]


def muat_train():
    e = pd.read_csv("data/processed/emails_clean.csv", usecols=["content_hash", "label", "body_text"])
    s = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
    m = e.merge(s, on="content_hash", validate="one_to_one")
    m = m[m["split"] == "train"].copy()
    assert len(m) == N_TRAIN, len(m)
    assert m["label"].value_counts().to_dict() == JUMLAH_LABEL, m["label"].value_counts().to_dict()
    m["body_text"] = m["body_text"].fillna("")
    return m


def ringkas(nama, panjang):
    n = len(panjang)
    q = panjang.quantile([0.5, 0.9, 0.95, 0.99, 0.999])
    print(f"{nama}{'*' if n < 30 else ''}: n={n} median={q[0.5]:.0f} p90={q[0.9]:.0f} p95={q[0.95]:.0f} "
          f"p99={q[0.99]:.0f} p99.9={q[0.999]:.0f} maks={panjang.max()}")
    print("   lebih dari " + "; ".join(f"{b}: {(panjang > b).sum()}" for b in BATAS))


def main():
    m = muat_train()
    m["panjang"] = m["body_text"].str.len()
    ringkas("semua", m["panjang"])
    for label in JUMLAH_LABEL:
        ringkas(label, m.loc[m["label"] == label, "panjang"])


if __name__ == "__main__":
    main()