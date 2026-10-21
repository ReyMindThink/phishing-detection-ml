"""EDA bentuk lanjutan per kelas: charset, panjang, ukuran. Hanya agregat."""
import pandas as pd

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False)
urutan = ["ham", "spam", "phishing"]

print("=== Charset (% per kelas, 6 terbanyak secara keseluruhan) ===")
atas = df["charset"].replace("", "(kosong)").value_counts().head(6).index
tabel = pd.crosstab(df["label"], df["charset"].replace("", "(kosong)"), normalize="index") * 100
print(tabel.loc[urutan, atas].round(1).to_string())

print("\n=== Panjang body_text (karakter) per kelas ===")
df["len_body"] = df["body_text"].str.len()
print(df.groupby("label")["len_body"].describe(percentiles=[0.25, 0.5, 0.75]).loc[urutan].round(0).to_string())

print("\n=== Ukuran bagian HTML (byte), hanya email HTML ===")
print(df[df["has_html"]].groupby("label")["html_bytes"].median().loc[urutan].to_string())

print("\n=== Jumlah bagian (n_parts), rata-rata ===")
print(df.groupby("label")["n_parts"].mean().loc[urutan].round(2).to_string())
