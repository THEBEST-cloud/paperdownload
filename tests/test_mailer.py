from paperdl.mailer import plan_batches, send_pdfs

MB = 1024 * 1024


def test_plan_batches_packs_under_limit():
    sizes = [("a", 8 * MB), ("b", 8 * MB), ("c", 8 * MB)]
    batches = plan_batches(sizes, max_bytes=20 * MB)
    assert batches == [["a", "b"], ["c"]]


def test_plan_batches_oversized_alone():
    sizes = [("big", 30 * MB), ("a", 5 * MB)]
    batches = plan_batches(sizes, max_bytes=20 * MB)
    assert batches == [["big"], ["a"]]


def test_plan_batches_empty():
    assert plan_batches([], 20 * MB) == []


class FakeSMTP:
    def __init__(self):
        self.sent = []
        self.logged_in = False
    def login(self, u, p):
        self.logged_in = True
    def send_message(self, msg):
        self.sent.append(msg)
    def quit(self):
        pass


def test_send_pdfs_splits_into_emails(tmp_path):
    d = tmp_path / "pdfs"; d.mkdir()
    (d / "a.pdf").write_bytes(b"%PDF" + b"x" * (8 * MB))
    (d / "b.pdf").write_bytes(b"%PDF" + b"y" * (8 * MB))
    (d / "c.pdf").write_bytes(b"%PDF" + b"z" * (8 * MB))
    fake = FakeSMTP()
    cfg = {"host": "smtp.x", "port": 465, "user": "u@x", "password": "pw", "from_addr": "u@x", "ssl": True}
    res = send_pdfs(d, "to@y", cfg=cfg, smtp_factory=lambda: fake, max_bytes=20 * MB)
    assert res["ok"] is True
    assert res["files"] == 3
    assert res["emails"] == 2          # 8+8 in one, 8 in another
    assert fake.logged_in is True
    assert len(fake.sent) == 2


def test_send_pdfs_no_smtp_config(tmp_path):
    d = tmp_path / "pdfs"; d.mkdir(); (d / "a.pdf").write_bytes(b"%PDF")
    res = send_pdfs(d, "to@y", cfg={"host": "", "user": "", "password": "", "from_addr": "", "ssl": True})
    assert res["ok"] is False
    assert "SMTP" in res["error"]


def test_send_pdfs_no_files(tmp_path):
    d = tmp_path / "pdfs"; d.mkdir()
    cfg = {"host": "smtp.x", "port": 465, "user": "u", "password": "p", "from_addr": "u", "ssl": True}
    res = send_pdfs(d, "to@y", cfg=cfg, smtp_factory=lambda: object())
    assert res["ok"] is False
