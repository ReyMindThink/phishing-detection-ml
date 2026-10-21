from email import message_from_string

from src.email_parser import defang, domain_pengirim, ekstrak_metadata, parse_pesan

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