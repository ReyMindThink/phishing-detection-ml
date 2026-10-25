"""Tahap 6-1: ukuran subset 'sulit' (tolok ukur pengganti). Hanya TRAIN.
Hanya angka agregat; isi subjek TIDAK dicetak. Tanpa model."""
import pandas as pd

URUTAN = ["ham", "spam", "phishing"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "has_html",
                          "has_list_header", "n_headers", "subject"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df = df[df["split"] == "train"].reset_index(drop=True)      # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
for c in ["has_html", "has_list_header"]:
    df[c] = df[c].astype(str) == "True"
s = df["subject"].str.strip()
df["gaya_milis"] = s.str.match(r"(?i)re\s*:") | s.str.startswith("[")

H1 = df["has_html"]
H2 = H1 & ~df["has_list_header"]
H3 = H2 & ~df["gaya_milis"]
tot = df["label"].value_counts()[URUTAN]
print("Train:", tot.to_dict())

print("\n=== Ukuran subset (n per kelas | % dari kelas itu di seluruh train) ===")
for nama, m in [("H1 HTML", H1), ("H2 HTML tanpa header milis", H2),
                ("H3 H2 tanpa Re:/[ di subjek", H3)]:
    n = df.loc[m, "label"].value_counts().reindex(URUTAN).fillna(0).astype(int)
    print("%-30s ham=%4d (%4.1f%%) spam=%4d (%4.1f%%) phishing=%4d (%4.1f%%)" % (
        nama, n["ham"], n["ham"] / tot["ham"] * 100, n["spam"], n["spam"] / tot["spam"] * 100,
        n["phishing"], n["phishing"] / tot["phishing"] * 100))

print("\n=== H2: n per lipatan x kelas ===")
print(pd.crosstab(df.loc[H2, "fold"], df.loc[H2, "label"]).reindex(columns=URUTAN).to_string())
print("\n=== H2: n per file/subset x kelas (n<30 diberi tanda *) ===")
t = pd.crosstab(df.loc[H2, "subset"], df.loc[H2, "label"]).reindex(columns=URUTAN).fillna(0).astype(int)
t["catatan"] = ["ada n<30 *" if ((r > 0) & (r < 30)).any() else "" for r in t[URUTAN].values]
print(t.to_string())

print("\n=== H2: common support, n_headers per kelas (n dan % dari kelas di H2) ===")
bin_ = pd.cut(df.loc[H2, "n_headers"], [-1, 13, 17, 21, 25, 10**4],
              labels=["<=13", "14-17", "18-21", "22-25", ">=26"])
n = pd.crosstab(bin_, df.loc[H2, "label"]).reindex(columns=URUTAN)
pers = (n / n.sum() * 100).round(1)
print(pd.concat({"n": n, "%": pers}, axis=1).to_string())