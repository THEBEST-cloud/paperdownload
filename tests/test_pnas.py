from paperdl.adapters.pnas import article_url, pdf_url
from paperdl.dispatch import adapter_key_for


def test_article_url():
    assert article_url("10.1073/pnas.1810141115") == "https://www.pnas.org/doi/10.1073/pnas.1810141115"


def test_pdf_url_has_download_flag():
    assert pdf_url("10.1073/pnas.1810141115") == \
        "https://www.pnas.org/doi/pdf/10.1073/pnas.1810141115?download=true"


def test_dispatch_pnas_by_prefix():
    assert adapter_key_for("", "10.1073/pnas.1810141115") == "pnas"
