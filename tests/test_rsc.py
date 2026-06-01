from paperdl.adapters.rsc import pdf_url_from_landing


def test_transform_landing_to_pdf():
    assert pdf_url_from_landing(
        "https://pubs.rsc.org/en/content/articlelanding/2020/sc/d0sc01746a"
    ) == "https://pubs.rsc.org/en/content/articlepdf/2020/sc/d0sc01746a"


def test_strips_query_and_fragment():
    assert pdf_url_from_landing(
        "https://pubs.rsc.org/en/content/articlelanding/2013/cs/c2cs35255a?foo=1#bar"
    ) == "https://pubs.rsc.org/en/content/articlepdf/2013/cs/c2cs35255a"


def test_none_for_non_landing_url():
    assert pdf_url_from_landing("https://pubs.rsc.org/en/journals/journalissues/cs") is None
