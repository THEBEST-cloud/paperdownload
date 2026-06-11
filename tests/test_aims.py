from paperdl.adapters.aims import article_url, find_pdf_url
from paperdl.dispatch import adapter_key_for


def test_article_url():
    assert article_url("10.3934/geosci.2017.2.216") == \
        "https://www.aimspress.com/article/10.3934/geosci.2017.2.216"


def test_find_pdf_url_absolute():
    html = '<a href="https://www.aimspress.com/aimspress-data/aimsgeo/2017/2/PDF/geosci-03-00216.pdf">Download PDF</a>'
    assert find_pdf_url(html) == "https://www.aimspress.com/aimspress-data/aimsgeo/2017/2/PDF/geosci-03-00216.pdf"


def test_find_pdf_url_relative():
    html = '<a href="/aimspress-data/aimsgeo/2017/2/PDF/geosci-03-00216.pdf">PDF</a>'
    assert find_pdf_url(html) == "https://www.aimspress.com/aimspress-data/aimsgeo/2017/2/PDF/geosci-03-00216.pdf"


def test_find_pdf_url_none():
    assert find_pdf_url('<a href="/article/x">HTML</a>') is None


def test_dispatch_aims_by_prefix():
    assert adapter_key_for("", "10.3934/geosci.2017.2.216") == "aims"
