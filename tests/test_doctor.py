import shutil
from pathlib import Path
import paperdl.doctor as doc


def test_check_proxy_env_warns_when_set():
    c = doc.check_proxy_env({"https_proxy": "http://127.0.0.1:7897"})
    assert c.status == "warn"


def test_check_proxy_env_ok_when_clean():
    assert doc.check_proxy_env({}).status == "ok"


def test_check_env_missing_file(tmp_path):
    assert doc.check_env(tmp_path).status == "fail"


def test_check_env_missing_required(tmp_path):
    (tmp_path / ".paperdl.env").write_text("ELSEVIER_API_KEY=k\n", encoding="utf-8")
    assert doc.check_env(tmp_path).status == "fail"


def test_check_env_ok(tmp_path):
    (tmp_path / ".paperdl.env").write_text("CSTCLOUD_ID=a@b\nCSTCLOUD_PASSWORD=p\n", encoding="utf-8")
    assert doc.check_env(tmp_path).status == "ok"


def test_check_xvfb_uses_which(monkeypatch):
    monkeypatch.setattr(doc.shutil, "which", lambda n: "/usr/bin/Xvfb")
    assert doc.check_xvfb().status == "ok"
    monkeypatch.setattr(doc.shutil, "which", lambda n: None)
    assert doc.check_xvfb().status == "fail"


def test_run_doctor_returns_int(tmp_path):
    rc = doc.run_doctor(base=tmp_path)
    assert isinstance(rc, int)
