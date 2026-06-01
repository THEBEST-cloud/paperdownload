from pathlib import Path
from paperdl.adapters.nature import find_pdf_url

FIX = Path(__file__).parent / "fixtures"


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
