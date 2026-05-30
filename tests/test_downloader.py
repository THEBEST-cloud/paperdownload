from pathlib import Path

from paperdl.downloader import download_one, DownloadContext
from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata


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
