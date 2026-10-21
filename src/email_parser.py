"""Parser email aman: mengubah satu pesan menjadi satu baris fitur teks.

Aman: tidak merender HTML, tidak men-decode lampiran, hanya membaca teks.
Output hanya string dan angka.
"""
import re
from email.message import Message
from email.utils import parseaddr
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

def ekstrak_metadata(msg: Message) -> dict:
    """Metadata BENTUK email (angka/kategori). Tanpa isi, tanpa decode lampiran.

    Dipakai untuk mendeteksi jalan pintas dataset (Tahap 6), bukan otomatis
    menjadi fitur model.
    """
    nama = [k.lower() for k in msg.keys()]
    html_bytes = 0
    plain_bytes = 0
    charset = ""
    n_bagian = 0
    for part in msg.walk():
        if part.is_multipart() or part.get_filename():
            continue
        n_bagian += 1
        tipe = part.get_content_type()
        if tipe not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True) or b""
        if tipe == "text/html":
            html_bytes += len(payload)
        else:
            plain_bytes += len(payload)
        if not charset:
            charset = (part.get_content_charset() or "").lower()
    return {
        "n_headers": len(nama),
        "n_received": nama.count("received"),
        "has_list_header": any(n.startswith("list-") for n in nama),
        "has_mailman": "x-mailman-version" in nama,
        "has_message_id": "message-id" in nama,
        "has_x_mailer": "x-mailer" in nama,
        "content_type": msg.get_content_type(),
        "charset": charset,
        "n_parts": n_bagian,
        "has_html": html_bytes > 0,
        "has_plain": plain_bytes > 0,
        "html_bytes": html_bytes,
        "plain_bytes": plain_bytes,
    }

def domain_pengirim(msg: Message) -> str:
    """Hanya DOMAIN dari header From (huruf kecil). Alamat lengkap tidak disimpan.
    Dipakai untuk pengelompokan split (cegah kebocoran pengirim), BUKAN sebagai
    fitur model.
    """
    alamat = parseaddr(str(msg.get("From", "")))[1]
    if "@" not in alamat:
        return ""
    return alamat.rsplit("@", 1)[1].strip().lower().rstrip(">.")