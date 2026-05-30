from pathlib import Path

from paperdl.adapters.springer import find_pdf_url

FIX = Path(__file__).parent / "fixtures"


def test_find_pdf_url_resolves_relative_link():
    html = (FIX / "springer_article.html").read_text()
    url = find_pdf_url(html, base_url="https://link-springer-com.proxy.las.ac.cn/article/10.1007/s00339-021-04567-w")
    assert url == "https://link-springer-com.proxy.las.ac.cn/content/pdf/10.1007/s00339-021-04567-w.pdf"


def test_find_pdf_url_returns_none_when_absent():
    assert find_pdf_url("<html><body>no link</body></html>", base_url="https://x.com/a") is None
