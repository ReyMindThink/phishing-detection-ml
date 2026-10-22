"""EDA domain pengirim per kelas. Hanya nama domain dan angka agregat."""
import pandas as pd

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False)
ada = df[df["sender_domain"] != ""]
print("Email dengan domain terbaca:", len(ada), "dari", len(df))

for label in ["ham", "spam", "phishing"]:
    g = ada[ada["label"] == label]["sender_domain"]
    atas = g.value_counts()
    print(f"\n=== {label}: {g.nunique()} domain unik, "
          f"10 teratas = {atas.head(10).sum() / len(g) * 100:.1f}% (tanpa domain kosong) ===")
    print(atas.head(10).to_string())

per_domain = ada.groupby("sender_domain")["label"].nunique()
print("\nDomain yang muncul di lebih dari satu kelas:", int((per_domain > 1).sum()))
print(ada[ada["sender_domain"].isin(per_domain[per_domain > 1].index)]
      .groupby("sender_domain")["label"].value_counts().head(20).to_string())