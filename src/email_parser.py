"""Parser email aman: mengubah satu pesan menjadi satu baris fitur teks.

Aman: tidak merender HTML, tidak men-decode lampiran, hanya membaca teks.
Output hanya string dan angka.
"""
import re
from email.message import Message
from email.utils import parseaddr
from html.parser import HTMLParser
from urllib.parse import urlsplit

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

# ---------------------------------------------------------------------------
# Fitur link (Tahap 5). Satu fungsi yang SAMA untuk semua kelas.
# Hanya string dan angka; tidak merender HTML dan tidak membuka link.
# ---------------------------------------------------------------------------
HOST_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
TEKS_DOMAIN_RE = re.compile(
    r"^(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?:[/:?#]|$)", re.IGNORECASE)


class _LinkDariHtml(HTMLParser):
    """Kumpulkan (href, teks_tampil) tiap <a>, plus jumlah <img> dan <form>."""

    def __init__(self):
        super().__init__()
        self.anchor = []
        self.n_images = 0
        self.n_forms = 0
        self._href = None
        self._teks = []
        self._abaikan = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self._abaikan += 1
        elif tag == "a" and a.get("href"):
            self._tutup()
            self._href = a["href"].strip()
            self._teks = []
        elif tag == "img":
            self.n_images += 1
        elif tag == "form":
            self.n_forms += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._abaikan:
            self._abaikan -= 1
        elif tag == "a":
            self._tutup()

    def handle_data(self, data):
        if self._href is not None and not self._abaikan:
            self._teks.append(data)

    def close(self):
        super().close()
        self._tutup()

    def _tutup(self):
        if self._href is not None:
            self.anchor.append((self._href, " ".join(" ".join(self._teks).split())))
        self._href = None
        self._teks = []


def _baca_bagian(part: Message):
    """Decode satu bagian text/*. (Mirip ambil_teks; sengaja tidak diubah agar
    data lama tetap sama. Bisa digabung nanti.)"""
    payload = part.get_payload(decode=True)
    if payload is None:
        return None
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _info_url(url: str):
    """(host, ada_userinfo) untuk URL http(s) absolut; selain itu None."""
    try:
        bagian = urlsplit(url)
        host = (bagian.hostname or "").rstrip(".")
    except ValueError:
        return None
    if bagian.scheme.lower() not in ("http", "https") or not host:
        return None
    return host, "@" in bagian.netloc


def _sama_domain(a: str, b: str) -> bool:
    a, b = a.removeprefix("www."), b.removeprefix("www.")
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def fitur_link(msg: Message) -> dict:
    """Angka tentang link di email. Domain disimpan defanged, tanpa path."""
    anchors, urls = [], []
    n_img = n_form = 0
    for part in msg.walk():
        if part.get_filename():
            continue
        tipe = part.get_content_type()
        if tipe not in ("text/plain", "text/html"):
            continue
        teks = _baca_bagian(part)
        if teks is None:
            continue
        if tipe == "text/html":
            p = _LinkDariHtml()
            p.feed(teks)
            p.close()
            anchors += p.anchor
            urls += [href for href, _ in p.anchor]
            n_img += p.n_images
            n_form += p.n_forms
        else:
            urls += URL_RE.findall(teks)

    info = {}                                  # url unik -> (host, userinfo)
    for u in dict.fromkeys(urls):
        hasil = _info_url(u)
        if hasil:
            info[u] = hasil
    hosts = [h for h, _ in info.values()]

    n_mismatch = 0
    for href, tampil in anchors:
        tujuan = _info_url(href)
        m = TEKS_DOMAIN_RE.match(tampil)
        if tujuan and m and not _sama_domain(m.group(1).lower(), tujuan[0]):
            n_mismatch += 1

    return {
        "n_links": len(info),
        "n_link_domains": len(set(hosts)),
        "domains_link_defanged": " ".join(dict.fromkeys(h.replace(".", "[.]") for h in hosts)),
        "n_link_mismatch": n_mismatch,
        "n_link_ip": sum(1 for h in hosts if HOST_IP_RE.match(h)),
        "n_link_userinfo": sum(1 for _, ada in info.values() if ada),
        "n_link_punycode": sum(1 for h in hosts if "xn--" in h),
        "max_url_len": max((len(u) for u in info), default=0),
        "max_host_labels": max((h.count(".") + 1 for h in hosts), default=0),
        "n_images": n_img,
        "n_forms": n_form,
    }

def nama_header(msg: Message) -> str:
    """Nama header unik (huruf kecil, urut abjad, dipisah spasi). TANPA isi.

    Hanya untuk diagnostik artefak dataset (Tahap 6), BUKAN fitur model.
    """
    return " ".join(sorted({k.lower() for k in msg.keys()}))
