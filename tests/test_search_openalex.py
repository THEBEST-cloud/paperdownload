# tests/test_search_openalex.py
import json
from pathlib import Path

from paperdl.search.base import SearchQuery
from paperdl.search.openalex import (
    reconstruct_abstract, build_params, parse_response, OpenAlexSource,
)

FIX = Path(__file__).parent / "fixtures" / "openalex_works.json"


def test_reconstruct_abstract():
    inv = {"Hello": [0], "world": [1], "again": [2]}
    assert reconstruct_abstract(inv) == "Hello world again"


def test_reconstruct_abstract_empty():
    assert reconstruct_abstract(None) == ""
    assert reconstruct_abstract({}) == ""


def test_build_params_basic():
    p = build_params(SearchQuery(query="microplastics"), mailto="a@b.cn")
    assert p["search"] == "microplastics"
    assert p["filter"] == "type:article"
    assert p["mailto"] == "a@b.cn"
    assert "sort" not in p


def test_build_params_filters_and_sort():
    q = SearchQuery(query="x", year_from=2020, year_to=2025, oa_only=True, sort="cited")
    p = build_params(q, mailto=None)
    assert "from_publication_date:2020-01-01" in p["filter"]
    assert "to_publication_date:2025-12-31" in p["filter"]
    assert "is_oa:true" in p["filter"]
    assert p["sort"] == "cited_by_count:desc"
    assert "mailto" not in p


def test_parse_response_maps_fields():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    page = parse_response(data)
    assert page.total > 0
    first = page.results[0]
    assert first.title
    assert first.doi and not first.doi.startswith("http")
    assert isinstance(first.authors, list)
    # fixture 第二条 abstract_inverted_index 为 null
    assert page.results[1].abstract == ""


def test_search_uses_injected_client(monkeypatch):
    data = json.loads(FIX.read_text(encoding="utf-8"))

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return data

    class FakeClient:
        def __init__(self): self.last = None
        def get(self, url, params=None):
            self.last = (url, params)
            return FakeResp()

    fake = FakeClient()
    src = OpenAlexSource(mailto="a@b.cn", client=fake)
    page = src.search(SearchQuery(query="x"))
    assert page.total > 0
    assert "openalex.org/works" in fake.last[0]
