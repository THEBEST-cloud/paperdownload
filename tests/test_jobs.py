from paperdl.web.jobs import JobManager, Job


def test_create_and_get(tmp_path):
    mgr = JobManager(base=tmp_path)
    job = mgr.create("job1", "2026-01-01T00:00:00", ["10.1/a", "10.1/b"])
    assert mgr.get("job1") is job
    assert job.total == 2
    assert set(job.items.keys()) == {"10.1/a", "10.1/b"}


def test_persist_and_reload(tmp_path):
    mgr = JobManager(base=tmp_path)
    mgr.create("job1", "2026-01-01T00:00:00", ["10.1/a"])
    mgr2 = JobManager(base=tmp_path)  # reloads from disk
    assert mgr2.get("job1") is not None
    assert mgr2.get("job1").total == 1


def test_list_sorted_desc(tmp_path):
    mgr = JobManager(base=tmp_path)
    mgr.create("a", "2026-01-01T00:00:00", ["10.1/a"])
    mgr.create("b", "2026-01-02T00:00:00", ["10.1/b"])
    assert [j.id for j in mgr.list()] == ["b", "a"]
