from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "make_skill", Path(__file__).resolve().parents[1] / "scripts" / "make_skill.py")
make_skill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_skill)


def _fake_repo(root: Path):
    (root / "paperdl").mkdir(parents=True)
    (root / "paperdl" / "cli.py").write_text("x=1\n")
    (root / "paperdl" / "__pycache__").mkdir()
    (root / "paperdl" / "__pycache__" / "cli.pyc").write_text("junk")
    (root / "pyproject.toml").write_text("[project]\n")
    # 隐私/产物：绝不能进包
    (root / ".paperdl.env").write_text("CSTCLOUD_PASSWORD=secret\n")
    (root / ".profile").mkdir()
    (root / ".profile" / "state").write_text("session")
    (root / "web_data").mkdir()
    (root / "web_data" / "users.json").write_text("{}")
    (root / "results.csv").write_text("doi\n")


def test_build_app_includes_source_excludes_secrets(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir()
    _fake_repo(repo)
    dest = tmp_path / "out"
    make_skill.build_app(repo, dest)
    assert (dest / "paperdl" / "cli.py").exists()
    assert (dest / "pyproject.toml").exists()
    # 脱敏：以下一律不存在
    assert list(dest.rglob(".paperdl.env")) == []
    assert list(dest.rglob("state")) == []          # .profile 内容
    assert list(dest.rglob("users.json")) == []
    assert list(dest.rglob("results.csv")) == []
    assert list(dest.rglob("*.pyc")) == []          # 跳过缓存
    assert list(dest.rglob(".profile")) == []      # .profile 目录本身也不应出现
