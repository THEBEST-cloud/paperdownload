from pathlib import Path

import paperdl.cli as cli
from paperdl.search.base import Paper, SearchPage


def _fake_source(papers):
    class S:
        def search(self, q):
            return SearchPage(results=papers, total=len(papers), page=1, per_page=25)
    return S()


def test_search_prints_table(monkeypatch, capsys):
    papers = [Paper(title="Hello world", authors=["A B"], year=2021,
                    doi="10.1/x", cited_by=5, is_oa=True)]
    monkeypatch.setattr(cli, "get_source", lambda *a, **k: _fake_source(papers))
    cli.main(["search", "hello"])
    out = capsys.readouterr().out
    assert "Hello world" in out
    assert "10.1/x" in out


def test_search_exports_doi_list(monkeypatch, tmp_path):
    papers = [Paper(title="X", doi="10.1/x"), Paper(title="Y", doi="10.2/y")]
    monkeypatch.setattr(cli, "get_source", lambda *a, **k: _fake_source(papers))
    out = tmp_path / "list.txt"
    cli.main(["search", "x", "-o", str(out)])
    assert out.read_text().split() == ["10.1/x", "10.2/y"]
