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
