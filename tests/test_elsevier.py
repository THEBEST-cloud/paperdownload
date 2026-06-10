from paperdl.adapters.elsevier import build_headers, classify_response, pdf_page_count

# 构造能被字节回退逻辑数出页数的假 PDF(pdfinfo 解析失败 -> 回退数 /Type/Page)
ONE_PAGE = b"%PDF-1.4\n/Type /Page \nstuff\n"
TWO_PAGE = b"%PDF-1.4\n/Type /Page \n/Type /Page \nstuff\n"


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


def test_pdf_page_count_fallback():
    assert pdf_page_count(ONE_PAGE) == 1
    assert pdf_page_count(TWO_PAGE) == 2


def test_classify_single_page_no_token_is_preview():
    # 无机构令牌 + 单页 PDF = Elsevier API 首页预览，应判失败
    r = classify_response(200, ONE_PAGE, has_insttoken=False)
    assert r.ok is False
    assert r.reason == "elsevier_preview"


def test_classify_single_page_with_token_is_ok():
    # 有机构令牌则信任结果(可能是真实的单页文章)
    r = classify_response(200, ONE_PAGE, has_insttoken=True)
    assert r.ok is True


def test_classify_multipage_no_token_is_ok():
    # 多页 PDF(通常是 OA 全文)即使无令牌也通过
    r = classify_response(200, TWO_PAGE, has_insttoken=False)
    assert r.ok is True
    assert r.pdf_bytes == TWO_PAGE
