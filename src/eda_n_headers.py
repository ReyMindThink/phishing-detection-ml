"""Bedah n_headers per subset (hanya data train). Hanya angka agregat."""
import pandas as pd

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False,
                 usecols=["content_hash", "label", "subset",
                          "n_headers", "n_received", "has_list_header"])
sp = pd.read_csv("data/processed/splits.csv", usecols=["content_hash", "split"])
df = df.merge(sp, on="content_hash", how="left", validate="one_to_one")
df = df[df["split"] == "train"]
print("Baris train:", len(df))

print("\n=== n_headers per subset: jumlah dan sebaran ===")
tabel = (df.groupby(["label", "subset"])["n_headers"]
         .describe(percentiles=[0.1, 0.5, 0.9])[["count", "min", "10%", "50%", "90%", "max"]])
print(tabel.round(0).to_string())

print("\n=== Pembanding per subset: n_received (median) dan % header mailing list ===")
ringkas = df.groupby(["label", "subset"]).agg(
    n_received_median=("n_received", "median"),
    persen_list=("has_list_header", lambda s: round(s.mean() * 100, 1)))
print(ringkas.to_string())

print("\n=== % email dengan n_headers <= batas, per kelas ===")
batas = (5, 10, 15, 20, 30)
cdf = pd.DataFrame({f"<={t}": df.groupby("label")["n_headers"]
                    .apply(lambda s, t=t: (s <= t).mean() * 100) for t in batas})
print(cdf.loc[["ham", "spam", "phishing"]].round(1).to_string())