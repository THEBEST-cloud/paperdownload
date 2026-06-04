from paperdl.web.jobs import JobManager


def test_create_with_owner_and_filtered_list(tmp_path):
    mgr = JobManager(base=tmp_path)
    mgr.create("j1", "2026-01-01T00:00:00", ["10.1/a"], owner="alice")
    mgr.create("j2", "2026-01-02T00:00:00", ["10.1/b"], owner="bob")
    assert [j.id for j in mgr.list(owner="alice")] == ["j1"]
    assert [j.id for j in mgr.list(owner="bob")] == ["j2"]
    assert len(mgr.list()) == 2  # no filter = all


def test_delete_job(tmp_path):
    mgr = JobManager(base=tmp_path)
    mgr.create("j1", "2026-01-01T00:00:00", ["10.1/a"], owner="alice")
    assert mgr.delete("j1") is True
    assert mgr.get("j1") is None
    assert (tmp_path / "web_data/jobs/j1").exists() is False


def test_new_job_is_queued(tmp_path):
    mgr = JobManager(base=tmp_path)
    j = mgr.create("j1", "2026-01-01T00:00:00", ["10.1/a"], owner="alice")
    assert j.status == "queued"
