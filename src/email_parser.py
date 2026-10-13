"""Parser email aman: mengubah satu pesan menjadi satu baris fitur teks.

Aman: tidak merender HTML, tidak men-decode lampiran, hanya membaca teks.
Output hanya string dan angka.
"""
import re
from email.message import Message
from html.parser import HTMLParser

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)


class _TeksDariHtml(HTMLParser):
    """Ambil teks dari HTML tanpa merender. Skrip dan style diabaikan."""

    def __init__(self):
        super().__init__()
        self.potongan = []
        self._abaikan = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._abaikan += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._abaikan:
            self._abaikan -= 1

    def handle_data(self, data):
        if not self._abaikan:
            self.potongan.append(data)


def html_ke_teks(html: str) -> str:
    p = _TeksDariHtml()
    p.feed(html)
    return " ".join(" ".join(p.potongan).split())


def defang(url: str) -> str:
    """hxxps://contoh[.]com agar tidak bisa diklik tidak sengaja."""
    url = re.sub(r"^http", "hxxp", url, flags=re.IGNORECASE)
    return url.replace(".", "[.]")


def ambil_teks(msg: Message) -> str:
    """Gabungkan bagian text/* saja. Lampiran dilewati tanpa di-decode."""
    hasil = []
    for part in msg.walk():
        if part.get_filename():
            continue
        tipe = part.get_content_type()
        if tipe not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            teks = payload.decode(charset, errors="replace")
        except LookupError:
            teks = payload.decode("utf-8", errors="replace")
        hasil.append(html_ke_teks(teks) if tipe == "text/html" else " ".join(teks.split()))
    return " ".join(hasil)


def parse_pesan(msg: Message) -> dict:
    teks = ambil_teks(msg)
    urls = URL_RE.findall(teks)
    lampiran = sum(1 for p in msg.walk() if p.get_filename())
    return {
        "subject": " ".join(str(msg.get("Subject", "")).split()),
        "body_text": teks,
        "n_urls": len(urls),
        "urls_defanged": [defang(u) for u in urls],
        "n_attachments": lampiran,
    }
