from paperdl.adapters.wiley import build_headers, classify_response


def test_build_headers():
    h = build_headers("TOK123")
    assert h["Wiley-TDM-Client-Token"] == "TOK123"
    assert h["Accept"] == "application/pdf"


def test_classify_pdf_ok():
    r = classify_response(200, b"%PDF-1.7 data")
    assert r.ok is True and r.pdf_bytes == b"%PDF-1.7 data"


def test_classify_non_pdf_is_no_pdf():
    r = classify_response(200, b"<html>not pdf</html>")
    assert r.ok is False and r.reason == "no_pdf"


def test_classify_403_no_access():
    assert classify_response(403, b"x").reason == "no_access"


def test_classify_401_no_access():
    assert classify_response(401, b"x").reason == "no_access"


def test_classify_500_error():
    assert classify_response(500, b"x").reason == "error"
