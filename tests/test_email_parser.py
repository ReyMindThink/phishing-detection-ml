from email import message_from_string

from src.email_parser import defang, domain_pengirim, ekstrak_metadata, fitur_link, nama_header, parse_pesan

CONTOH = (
    "Subject: [CONTOH FIKTIF] Verifikasi akun\n"
    "Content-Type: text/html; charset=utf-8\n\n"
    "<html><body><p>Klik <a href='http://example.com/x'>di sini</a></p>"
    "<script>alert(1)</script></body></html>"
)


def test_defang():
    assert defang("http://example.com/a") == "hxxp://example[.]com/a"


def test_parse_pesan_html_fiktif():
    hasil = parse_pesan(message_from_string(CONTOH))
    assert hasil["subject"] == "[CONTOH FIKTIF] Verifikasi akun"
    assert "alert" not in hasil["body_text"]
    assert hasil["n_attachments"] == 0


def test_metadata_bentuk_email_fiktif():
    pesan = message_from_string(
        "Received: from a.example.com\n"
        "Received: from b.example.com\n"
        "List-Id: <contoh.example.com>\n"
        "Subject: [CONTOH FIKTIF] tes\n"
        "Content-Type: text/plain; charset=us-ascii\n\n"
        "halo"
    )
    m = ekstrak_metadata(pesan)
    assert m["n_received"] == 2
    assert m["has_list_header"] is True
    assert m["has_html"] is False
    assert m["plain_bytes"] == 4
    assert m["charset"] == "us-ascii"


def test_metadata_html_tanpa_header_list():
    pesan = message_from_string(
        "Subject: [CONTOH FIKTIF]\n"
        "Content-Type: text/html; charset=iso-8859-1\n\n"
        "<p>halo</p>"
    )
    m = ekstrak_metadata(pesan)
    assert m["has_html"] is True
    assert m["has_list_header"] is False
    assert m["html_bytes"] == 11

def test_domain_pengirim():
    pesan = message_from_string(
        "From: Contoh Fiktif <Seseorang@Example.COM>\n"
        "Subject: x\n\nhalo"
    )
    assert domain_pengirim(pesan) == "example.com"

def test_domain_pengirim_kosong_atau_rusak():
    assert domain_pengirim(message_from_string("Subject: x\n\nhalo")) == ""
    assert domain_pengirim(message_from_string("From: tanpa-alamat\n\nhalo")) == ""

def _html(isi):
    return message_from_string(
        "Subject: [CONTOH FIKTIF]\nContent-Type: text/html; charset=utf-8\n\n" + isi)


def test_link_dari_href_html():
    pesan = message_from_string(CONTOH)
    f = fitur_link(pesan)
    assert f["n_links"] == 1
    assert f["domains_link_defanged"] == "example[.]com"
    assert f["n_link_mismatch"] == 0
    assert parse_pesan(pesan)["n_urls"] == 0   # kelemahan parser lama: href tidak terbaca


def test_link_mismatch_teks_vs_tujuan():
    beda = _html("<a href='http://example.net/x'>www.example.com/login</a>")
    assert fitur_link(beda)["n_link_mismatch"] == 1
    sama = _html("<a href='http://mail.example.com/x'>example.com</a>")
    assert fitur_link(sama)["n_link_mismatch"] == 0
    biasa = _html("<a href='http://example.net/x'>klik di sini</a>")
    assert fitur_link(biasa)["n_link_mismatch"] == 0


def test_link_ip_userinfo_punycode():
    f = fitur_link(_html(
        "<a href='http://192.0.2.1/a'>a</a>"
        "<a href='http://example.com@example.net/x'>b</a>"
        "<a href='http://xn--exmple-cua.example/'>c</a>"))
    assert f["n_links"] == 3
    assert f["n_link_ip"] == 1
    assert f["n_link_userinfo"] == 1
    assert f["n_link_punycode"] == 1


def test_url_teks_biasa_dan_deduplikasi():
    pesan = message_from_string(
        "Subject: [CONTOH FIKTIF]\nContent-Type: text/plain; charset=us-ascii\n\n"
        "Lihat http://example.com/a dan lagi http://example.com/a")
    f = fitur_link(pesan)
    assert f["n_links"] == 1
    assert f["n_link_domains"] == 1


def test_skema_lain_dan_relatif_diabaikan():
    f = fitur_link(_html("<a href='mailto:a@example.com'>x</a><a href='/lokal'>y</a>"
                         "<a href='javascript:void(0)'>z</a>"))
    assert f["n_links"] == 0
    assert f["max_url_len"] == 0


def test_tanpa_link_dan_html_rusak_tidak_error():
    kosong = fitur_link(message_from_string("Subject: x\n\nhalo"))
    assert kosong["n_links"] == 0
    assert kosong["domains_link_defanged"] == ""
    # yang diuji di sini hanya: HTML rusak tidak melempar error
    rusak = fitur_link(_html("<a href='http://example.com' <p><form><img src=x"))
    assert rusak["n_links"] >= 0


def test_hitung_form_dan_gambar():
    f = fitur_link(_html("<form action='http://example.com/p'><input name='u'></form>"
                         "<img src='x'><img src='y'>"))
    assert f["n_forms"] == 1
    assert f["n_images"] == 2

def test_nama_header_unik_urut_tanpa_isi():
    pesan = message_from_string(
        "Received: from a.example.com\n"
        "Received: from b.example.com\n"
        "X-Mailer: Contoh\n"
        "Subject: [CONTOH FIKTIF] rahasia123\n\n"
        "halo")
    hasil = nama_header(pesan)
    assert hasil == "received subject x-mailer"
    assert "rahasia123" not in hasil
    assert nama_header(message_from_string("")) == ""
    