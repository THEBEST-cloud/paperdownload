from paperdl.adapters.elsevier import build_headers, classify_response


def test_build_headers_basic():
    h = build_headers("KEY123")
    assert h["X-ELS-APIKey"] == "KEY123"
    assert h["Accept"] == "application/pdf"
    assert "X-ELS-Insttoken" not in h


def test_build_headers_with_insttoken():
    h = build_headers("KEY", insttoken="TOK")
    assert h["X-ELS-Insttoken"] == "TOK"


def test_classify_pdf_ok():
    r = classify_response(200, b"%PDF-1.7 data")
    assert r.ok is True
    assert r.pdf_bytes == b"%PDF-1.7 data"


def test_classify_non_pdf_200_is_no_pdf():
    r = classify_response(200, b"<full-text-retrieval-response>...")
    assert r.ok is False
    assert r.reason == "no_pdf"


def test_classify_403_is_no_access():
    assert classify_response(403, b"x").reason == "no_access"


def test_classify_401_is_no_access():
    assert classify_response(401, b"x").reason == "no_access"


def test_classify_500_is_error():
    assert classify_response(500, b"x").reason == "error"
