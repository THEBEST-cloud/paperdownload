from pathlib import Path

from paperdl.downloader import download_one, DownloadContext
from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata
from paperdl.results import ResultStore


class FakeAdapter:
    key = "fake"
    def __init__(self, result):
        self._result = result
    def download(self, page, md):
        return self._result


def test_download_one_success_writes_pdf(tmp_path):
    md = Metadata(doi="10.1/a", first_author="Zhang", year=2021, title="T",
                  publisher="Springer")
    adapter = FakeAdapter(DownloadResult(ok=True, pdf_bytes=b"%PDF-1.7 data"))
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={"fake": adapter})
    row = download_one(md, "fake", ctx)
    assert row.status == "success"
    assert (tmp_path / row.file_path).read_bytes().startswith(b"%PDF")


def test_download_one_failure_records_reason(tmp_path):
    md = Metadata(doi="10.1/b", publisher="Springer")
    adapter = FakeAdapter(DownloadResult(ok=False, reason="no_access"))
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={"fake": adapter})
    row = download_one(md, "fake", ctx)
    assert row.status == "failed"
    assert row.reason == "no_access"
    assert row.file_path == ""


def test_download_one_unknown_adapter(tmp_path):
    md = Metadata(doi="10.1/c", publisher="Tiny Press")
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={})
    row = download_one(md, None, ctx)
    assert row.status == "failed"
    assert row.reason == "no_adapter"


def test_run_metadata_failure_is_recorded_and_continues(tmp_path, monkeypatch):
    import paperdl.downloader as d
    monkeypatch.setattr(d, "fetch_metadata",
                        lambda doi, client=None: (_ for _ in ()).throw(RuntimeError("crossref down")))
    monkeypatch.setattr(d.time, "sleep", lambda s: None)
    list_path = tmp_path / "l.txt"
    list_path.write_text("10.1/bad\n")
    store = ResultStore(tmp_path / "results.csv")
    ctx = DownloadContext(page=None, out_dir=tmp_path / "dl", adapters={})
    d.run(list_path, ctx, store)
    assert ResultStore(tmp_path / "results.csv").failed_dois() == ["10.1/bad"]


def test_run_does_not_retry_terminal(tmp_path, monkeypatch):
    import paperdl.downloader as d
    monkeypatch.setattr(d, "fetch_metadata",
                        lambda doi, client=None: Metadata(doi="10.1007/x", publisher="Springer"))
    monkeypatch.setattr(d.time, "sleep", lambda s: None)
    monkeypatch.setattr(d.random, "uniform", lambda a, b: 0)
    calls = {"n": 0}
    class A:
        key = "springer"
        def download(self, page, m):
            calls["n"] += 1
            return DownloadResult(ok=False, reason="no_access")
    store = ResultStore(tmp_path / "r.csv")
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={"springer": A()})
    list_path = tmp_path / "l.txt"; list_path.write_text("10.1007/x\n")
    d.run(list_path, ctx, store)
    assert calls["n"] == 1


def test_run_retries_transient_timeout(tmp_path, monkeypatch):
    import paperdl.downloader as d
    monkeypatch.setattr(d, "fetch_metadata",
                        lambda doi, client=None: Metadata(doi="10.1007/x", publisher="Springer"))
    monkeypatch.setattr(d.time, "sleep", lambda s: None)
    monkeypatch.setattr(d.random, "uniform", lambda a, b: 0)
    calls = {"n": 0}
    class A:
        key = "springer"
        def download(self, page, m):
            calls["n"] += 1
            return DownloadResult(ok=False, reason="timeout")
    store = ResultStore(tmp_path / "r.csv")
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={"springer": A()})
    list_path = tmp_path / "l.txt"; list_path.write_text("10.1007/x\n")
    d.run(list_path, ctx, store)
    assert calls["n"] == 3  # 1 initial + 2 retries (RETRIES=2)


def test_run_calls_progress_callback(tmp_path, monkeypatch):
    import paperdl.downloader as d
    monkeypatch.setattr(d, "fetch_metadata", lambda doi, client=None: Metadata(doi=doi, publisher="X"))
    monkeypatch.setattr(d.time, "sleep", lambda s: None)
    monkeypatch.setattr(d.random, "uniform", lambda a, b: 0)
    calls = []
    list_path = tmp_path / "l.txt"; list_path.write_text("10.1/a\n10.1/b\n")
    store = ResultStore(tmp_path / "r.csv")
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={})
    d.run(list_path, ctx, store, progress=lambda i, total, row: calls.append((i, total, row.doi)))
    assert [(c[0], c[1]) for c in calls] == [(1, 2), (2, 2)]


def test_download_one_avoids_overwrite_on_collision(tmp_path):
    a = Metadata(doi="10.1/a", first_author="Li", year=2020, title="Same Title", publisher="X")
    b = Metadata(doi="10.1/b", first_author="Li", year=2020, title="Same Title", publisher="X")
    ctx_a = DownloadContext(page=None, out_dir=tmp_path,
                            adapters={"fake": FakeAdapter(DownloadResult(ok=True, pdf_bytes=b"%PDF-a"))})
    ctx_b = DownloadContext(page=None, out_dir=tmp_path,
                            adapters={"fake": FakeAdapter(DownloadResult(ok=True, pdf_bytes=b"%PDF-b"))})
    r1 = download_one(a, "fake", ctx_a)
    r2 = download_one(b, "fake", ctx_b)
    assert r1.status == "success" and r2.status == "success"
    assert r1.file_path != r2.file_path
    assert (tmp_path / r1.file_path).read_bytes() == b"%PDF-a"
    assert (tmp_path / r2.file_path).read_bytes() == b"%PDF-b"
