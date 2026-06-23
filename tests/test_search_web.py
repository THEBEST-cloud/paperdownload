# tests/test_search_web.py
import paperdl.web.app as webapp
from paperdl.search.base import Paper, SearchPage
from fastapi.testclient import TestClient


def _login_client(monkeypatch):
    # 绕过鉴权:直接覆盖依赖
    webapp.app.dependency_overrides[webapp.current_user] = lambda: "tester"
    return TestClient(webapp.app)


def test_search_route(monkeypatch):
    papers = [Paper(title="Hello", doi="10.1/x", year=2021, cited_by=3)]
    monkeypatch.setattr(webapp, "get_source",
                        lambda *a, **k: type("S", (), {"search": lambda self, q: SearchPage(results=papers, total=1)})())
    c = _login_client(monkeypatch)
    try:
        r = c.get("/api/search", params={"q": "hello"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["results"][0]["doi"] == "10.1/x"
    finally:
        webapp.app.dependency_overrides.clear()


def test_export_route(monkeypatch):
    c = _login_client(monkeypatch)
    try:
        r = c.post("/api/search/export",
                   json={"papers": [{"title": "X", "doi": "10.1/x", "authors": [], "year": 2020}],
                         "format": "doi"})
        assert r.status_code == 200
        assert "10.1/x" in r.text
    finally:
        webapp.app.dependency_overrides.clear()
