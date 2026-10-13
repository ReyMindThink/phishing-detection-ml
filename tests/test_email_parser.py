from email import message_from_string

from src.email_parser import defang, parse_pesan

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