"""EDA fitur link di data TRAIN, hanya email HTML (has_html = True).
Test set dibuang di awal. Hanya angka agregat."""
import pandas as pd

URUTAN = ["ham", "spam", "phishing"]
LINK = ["n_links", "n_link_mismatch", "n_link_ip", "n_forms", "n_images"]

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset", "has_html"] + LINK)
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split", "fold"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
assert df["split"].notna().all(), "ada email tanpa indeks split"
df["has_html"] = df["has_html"].astype(str) == "True"

print("Split semua data (bukti 7438/1860):")
print(pd.crosstab(df["split"], df["label"])[URUTAN].to_string())

df = df[df["split"] == "train"].reset_index(drop=True)   # TEST DIBUANG DI SINI
assert len(df) == 7438, len(df)
html = df[df["has_html"]]
print("\nTrain total:", len(df), "| email HTML:", len(html))

print("\n=== Ukuran sel: email HTML per subset (train) ===")
ukuran = pd.DataFrame({"n_train": df.groupby("subset").size(),
                       "n_html": html.groupby("subset").size()}).fillna(0).astype(int)
ukuran["%html"] = (ukuran["n_html"] / ukuran["n_train"] * 100).round(1)
print(ukuran.to_string())


def ringkas(g):
    return {"n": len(g),
            "med_links": g["n_links"].median(),
            "p90_links": g["n_links"].quantile(0.9),
            "%link=0": (g["n_links"] == 0).mean() * 100,
            "%mismatch": (g["n_link_mismatch"] > 0).mean() * 100,
            "%ip": (g["n_link_ip"] > 0).mean() * 100,
            "%form": (g["n_forms"] > 0).mean() * 100,
            "%img": (g["n_images"] > 0).mean() * 100}


def tabel(kunci):
    t = pd.DataFrame({k: ringkas(g) for k, g in html.groupby(kunci)}).T
    t["n"] = t["n"].astype(int)
    t["catatan"] = ["n<30 *" if n < 30 else "" for n in t["n"]]
    return t.round(1)


print("\n=== Fitur link, email HTML saja, per KELAS ===")
print(tabel("label").loc[URUTAN].to_string())
print("\n=== Fitur link, email HTML saja, per SUBSET ===")
print(tabel("subset").to_string())

print("\n=== Email HTML per lipatan CV x kelas (untuk uji CV nanti) ===")
print(pd.crosstab(html["fold"], html["label"])[URUTAN].to_string())