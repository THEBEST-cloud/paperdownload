from pathlib import Path
from paperdl.adapters.nature import find_pdf_url, classify_non_pdf

FIX = Path(__file__).parent / "fixtures"


def test_classify_paywall_html_is_no_access():
    # 机构无订阅时，.pdf 端点返回的是文章/付费墙 HTML（200），应判为 no_access 而非 blocked
    html = (b"<!DOCTYPE html><html><head><title>X | Nature Water</title></head>"
            b"<body>Get access ... Buy Now $39.95 ... readcube</body></html>")
    assert classify_non_pdf(html) == "no_access"


def test_classify_cloudflare_is_blocked():
    # Cloudflare 反爬挑战页是可重试的 blocked，不能误判成 no_access
    cf = (b"<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
          b"<body>cf-browser-verification challenge-platform</body></html>")
    assert classify_non_pdf(cf) == "blocked"


def test_classify_non_html_garbage_is_blocked():
    assert classify_non_pdf(b"\x00\x01\x02 not html not pdf") == "blocked"


def test_find_pdf_url_from_meta():
    html = (FIX / "nature_article.html").read_text()
    url = find_pdf_url(html, base_url="https://www.nature.com/articles/nature14539")
    assert url == "https://www.nature.com/articles/nature14539.pdf"


def test_find_pdf_url_fallback_appends_pdf():
    # 没有 meta 时，回退为文章 URL 加 .pdf
    url = find_pdf_url("<html><head></head><body>x</body></html>",
                       base_url="https://www.nature.com/articles/s41586-020-2649-2")
    assert url == "https://www.nature.com/articles/s41586-020-2649-2.pdf"


def test_find_pdf_url_none_for_non_article():
    assert find_pdf_url("<html></html>", base_url="https://www.nature.com/") is None
