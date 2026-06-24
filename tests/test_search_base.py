from paperdl.search.base import Paper, SearchQuery, SearchPage


def test_paper_defaults():
    p = Paper(title="Hello")
    assert p.authors == []
    assert p.year is None
    assert p.cited_by == 0
    assert p.is_oa is False
    assert p.doi is None


def test_searchquery_defaults():
    q = SearchQuery(query="microplastics")
    assert q.sort == "relevance"
    assert q.work_type == "article"
    assert q.page == 1
    assert q.per_page == 25


def test_searchpage_defaults():
    sp = SearchPage()
    assert sp.results == []
    assert sp.total == 0
