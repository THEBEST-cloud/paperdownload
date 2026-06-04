from paperdl import xvfb


def test_ensure_display_sets_env(monkeypatch):
    # 不真启动：伪造锁文件已存在的分支
    import paperdl.xvfb as x
    monkeypatch.setattr(x.Path, "exists", lambda self: True)
    monkeypatch.delenv("DISPLAY", raising=False)
    d = xvfb.ensure_display(":99")
    assert d == ":99"
    import os
    assert os.environ["DISPLAY"] == ":99"
