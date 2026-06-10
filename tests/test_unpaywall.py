from paperdl.adapters.unpaywall import oa_pdf_urls


def test_best_location_pdf_first():
    data = {"best_oa_location": {"url_for_pdf": "http://repo/best.pdf"},
            "oa_locations": [{"url_for_pdf": "http://repo/other.pdf"}]}
    assert oa_pdf_urls(data)[0] == "http://repo/best.pdf"


def test_dedup_best_and_locations():
    data = {"best_oa_location": {"url_for_pdf": "http://repo/x.pdf"},
            "oa_locations": [{"url_for_pdf": "http://repo/x.pdf"},
                             {"url_for_pdf": "http://repo/y.pdf"}]}
    assert oa_pdf_urls(data) == ["http://repo/x.pdf", "http://repo/y.pdf"]


def test_falls_back_to_url_when_no_pdf_field():
    data = {"oa_locations": [{"url": "http://repo/landing"}]}
    assert oa_pdf_urls(data) == ["http://repo/landing"]


def test_empty_when_not_oa():
    assert oa_pdf_urls({"is_oa": False, "best_oa_location": None, "oa_locations": []}) == []


def test_handles_missing_keys():
    assert oa_pdf_urls({}) == []
