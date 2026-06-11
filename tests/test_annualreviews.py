from paperdl.adapters.annualreviews import article_url, pdf_url
from paperdl.dispatch import adapter_key_for
from paperdl.shibboleth import ADAPTER_ENTRY, ENTRY_MATCH


def test_article_url():
    assert article_url("10.1146/annurev-earth-040523-020630") == \
        "https://www.annualreviews.org/doi/10.1146/annurev-earth-040523-020630"


def test_pdf_url_has_download_flag():
    assert pdf_url("10.1146/annurev-earth-040523-020630") == \
        "https://www.annualreviews.org/doi/pdf/10.1146/annurev-earth-040523-020630?download=true"


def test_dispatch_by_prefix():
    assert adapter_key_for("", "10.1146/annurev-earth-040523-020630") == "annualreviews"


def test_shib_wiring():
    assert ADAPTER_ENTRY.get("annualreviews") == "annualreviews"
    assert "annualreviews" in ENTRY_MATCH
