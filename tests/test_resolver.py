import json
from pathlib import Path

from paperdl.resolver import parse_crossref, Metadata

FIX = Path(__file__).parent / "fixtures"


def test_parse_crossref_extracts_fields():
    raw = json.loads((FIX / "crossref_springer.json").read_text())
    md = parse_crossref("10.1007/s00339-021-04567-w", raw)
    assert isinstance(md, Metadata)
    assert md.doi == "10.1007/s00339-021-04567-w"
    assert md.publisher == "Springer Science and Business Media LLC"
    assert md.title == "A study of something interesting"
    assert md.container == "Applied Physics A"
    assert md.first_author == "Zhang"
    assert md.year == 2021
    assert md.url == "https://dx.doi.org/10.1007/s00339-021-04567-w"


def test_parse_crossref_missing_optional_fields():
    md = parse_crossref("10.1/x", {"message": {"DOI": "10.1/x"}})
    assert md.doi == "10.1/x"
    assert md.publisher == ""
    assert md.title == ""
    assert md.first_author == ""
    assert md.year is None


def test_parse_crossref_extracts_links():
    raw = {"message": {"DOI": "10.5194/x", "link": [
        {"URL": "https://ex.org/a.pdf", "content-type": "application/pdf", "intended-application": "text-mining"},
        {"URL": "https://ex.org/b.html", "content-type": "text/html", "intended-application": "text-mining"},
    ]}}
    md = parse_crossref("10.5194/x", raw)
    assert md.links == [
        {"url": "https://ex.org/a.pdf", "content_type": "application/pdf", "intended_application": "text-mining"},
        {"url": "https://ex.org/b.html", "content_type": "text/html", "intended_application": "text-mining"},
    ]


def test_parse_crossref_links_default_empty():
    md = parse_crossref("10.1/x", {"message": {"DOI": "10.1/x"}})
    assert md.links == []
