from paperdl.adapters.science import article_url, pdf_url
from paperdl.dispatch import adapter_key_for


def test_article_url():
    assert article_url("10.1126/science.aap8826") == "https://www.science.org/doi/10.1126/science.aap8826"


def test_pdf_url_has_download_flag():
    assert pdf_url("10.1126/science.aap8826") == \
        "https://www.science.org/doi/pdf/10.1126/science.aap8826?download=true"


def test_dispatch_science_by_prefix():
    assert adapter_key_for("", "10.1126/science.aap8826") == "science"


def test_dispatch_science_by_keyword():
    assert adapter_key_for("American Association for the Advancement of Science (AAAS)",
                           "10.9999/x") == "science"
