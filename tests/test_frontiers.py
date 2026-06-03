from paperdl.adapters.frontiers import find_pdf_url


def test_find_pdf_url_from_meta():
    html = '<meta name="citation_pdf_url" content="https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2015.00063/pdf"/>'
    assert find_pdf_url(html, "https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2015.00063") \
        == "https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2015.00063/pdf"


def test_find_pdf_url_fallback_appends_pdf():
    url = find_pdf_url("<html></html>", "https://www.frontiersin.org/journals/x/articles/10.3389/foo.2020.00010")
    assert url == "https://www.frontiersin.org/journals/x/articles/10.3389/foo.2020.00010/pdf"


def test_find_pdf_url_strips_full_suffix():
    url = find_pdf_url("<html></html>", "https://www.frontiersin.org/articles/10.3389/foo.2020.00010/full")
    assert url == "https://www.frontiersin.org/articles/10.3389/foo.2020.00010/pdf"


def test_find_pdf_url_none_for_non_article():
    assert find_pdf_url("<html></html>", "https://www.frontiersin.org/") is None
