"""Grafik: sifat 'bentuk' email per kelas. Hanya persentase agregat."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False)
sifat = {"has_html": "HTML", "has_plain": "teks biasa",
         "has_list_header": "header mailing list", "has_mailman": "X-Mailman"}
urutan = ["ham", "spam", "phishing"]
persen = (df.groupby("label")[list(sifat)].mean() * 100).loc[urutan]
print(persen.round(1).to_string())

ax = persen.rename(columns=sifat).T.plot(kind="bar", figsize=(8, 4.5), rot=0)
ax.set_ylabel("% email")
ax.set_title("Bentuk email per kelas (setelah buang duplikat)")
ax.legend(title="kelas")
plt.tight_layout()
plt.savefig("reports/figures/shape_by_label.png", dpi=150)
print("Tersimpan: reports/figures/shape_by_label.png")