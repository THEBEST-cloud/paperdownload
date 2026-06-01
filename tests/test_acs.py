from paperdl.adapters.acs import pdf_url_for


def test_pdf_url_for_builds_doi_pdf_path():
    assert pdf_url_for("10.1021/jacs.9b13402") == "https://pubs.acs.org/doi/pdf/10.1021/jacs.9b13402"
