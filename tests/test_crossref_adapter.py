from paperdl.adapters.crossref import pdf_candidates


def test_pdf_candidates_prefers_application_pdf():
    links = [
        {"url": "https://x/a.html", "content_type": "text/html", "intended_application": "text-mining"},
        {"url": "https://x/b.pdf", "content_type": "application/pdf", "intended_application": "text-mining"},
    ]
    assert pdf_candidates(links) == ["https://x/b.pdf"]


def test_pdf_candidates_matches_pdf_in_url_when_no_content_type():
    links = [{"url": "https://x/c/pdf", "content_type": "unspecified", "intended_application": "similarity-checking"}]
    assert pdf_candidates(links) == ["https://x/c/pdf"]


def test_pdf_candidates_orders_textmining_before_similarity():
    links = [
        {"url": "https://x/sim.pdf", "content_type": "application/pdf", "intended_application": "similarity-checking"},
        {"url": "https://x/tdm.pdf", "content_type": "application/pdf", "intended_application": "text-mining"},
    ]
    assert pdf_candidates(links) == ["https://x/tdm.pdf", "https://x/sim.pdf"]


def test_pdf_candidates_empty_when_no_pdf():
    assert pdf_candidates([{"url": "https://x/a.html", "content_type": "text/html", "intended_application": "x"}]) == []
