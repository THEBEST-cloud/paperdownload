# tests/test_search_web.py
import httpx
import pytest
import paperdl.web.app as webapp
from paperdl.search.base import Paper, SearchPage
from fastapi import HTTPException


def test_search_route(monkeypatch):
    papers = [Paper(title="Hello", doi="10.1/x", year=2021, cited_by=3)]
    monkeypatch.setattr(webapp, "get_source",
                        lambda *a, **k: type("S", (), {"search": lambda self, q: SearchPage(results=papers, total=1)})())
    body = webapp.api_search(q="hello", user="tester")
    assert body["total"] == 1
    assert body["results"][0]["doi"] == "10.1/x"


def test_export_route(monkeypatch):
    r = webapp.api_search_export(
        {"papers": [{"title": "X", "doi": "10.1/x", "authors": [], "year": 2020}],
         "format": "doi"}, user="tester")
    assert r.status_code == 200
    assert b"10.1/x" in r.body


def test_download_route(monkeypatch):
    class FakeJob:
        id = "job-xyz"

    class FakeMgr:
        def create(self, *a, **k):
            return FakeJob()

        def start(self, job):
            pass

    monkeypatch.setattr(webapp, "mgr", FakeMgr())
    body = webapp.api_search_download({"dois": ["10.1/x", "10.2/y"]}, user="tester")
    assert body["job_id"] == "job-xyz"


def test_search_502_on_httpx_error(monkeypatch):
    # 模拟检索源抛出 httpx 网络错误，路由应返回 502
    class BrokenSource:
        def search(self, q):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(webapp, "get_source", lambda *a, **k: BrokenSource())
    with pytest.raises(HTTPException) as exc:
        webapp.api_search(q="x", user="tester")
    assert exc.value.status_code == 502
