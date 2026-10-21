"""Indikator struktural label mencurigakan. Hanya angka agregat."""
import pandas as pd

df = pd.read_csv("data/processed/emails_clean.csv", keep_default_na=False)
df["len_body"] = df["body_text"].str.len()
ph = df[df["label"] == "phishing"].copy()

print("Phishing:", len(ph))
teks_polos = ~ph["has_html"]
print("Tanpa HTML sama sekali:", int(teks_polos.sum()))
print("Tanpa HTML dan tanpa URL:", int((teks_polos & (ph["n_urls"] == 0)).sum()))
print("Tanpa HTML, tanpa URL, body < 300 karakter:",
      int((teks_polos & (ph["n_urls"] == 0) & (ph["len_body"] < 300)).sum()))
print("Body < 100 karakter (semua):", int((ph["len_body"] < 100).sum()))

print("\n=== Per file Nazario ===")
per_file = ph.groupby("source_file").agg(
    n=("label", "size"),
    persen_html=("has_html", lambda s: round(s.mean() * 100, 1)),
    persen_win1251=("charset", lambda s: round((s == "windows-1251").mean() * 100, 1)),
    persen_charset_kosong=("charset", lambda s: round((s == "").mean() * 100, 1)),
    persen_tanpa_html_tanpa_url=("n_urls", lambda s: 0),
)
per_file["persen_tanpa_html_tanpa_url"] = ph.groupby("source_file").apply(
    lambda g: round((~g["has_html"] & (g["n_urls"] == 0)).mean() * 100, 1),
    include_groups=False,
)
print(per_file.to_string())