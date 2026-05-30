from paperdl.results import ResultStore, ResultRow


def test_roundtrip_and_completed_set(tmp_path):
    path = tmp_path / "results.csv"
    store = ResultStore(path)
    store.record(ResultRow(doi="10.1/a", publisher="springer", title="T1",
                           status="success", reason="", file_path="downloads/a.pdf"))
    store.record(ResultRow(doi="10.1/b", publisher="springer", title="T2",
                           status="failed", reason="no_pdf", file_path=""))

    reloaded = ResultStore(path)
    assert reloaded.completed_dois() == {"10.1/a"}  # 只有 success 算完成
    assert "10.1/b" not in reloaded.completed_dois()


def test_failed_dois(tmp_path):
    path = tmp_path / "results.csv"
    store = ResultStore(path)
    store.record(ResultRow(doi="10.1/a", publisher="x", title="", status="success",
                           reason="", file_path="downloads/a.pdf"))
    store.record(ResultRow(doi="10.1/b", publisher="x", title="", status="failed",
                           reason="timeout", file_path=""))
    assert ResultStore(path).failed_dois() == ["10.1/b"]
