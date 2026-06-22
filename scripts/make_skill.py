"""把仓库脱敏打包成 Claude Code skill / Codex 包到目标目录。

用白名单（只拷运行所需）确保隐私/产物永不进包：根目录的 .paperdl.env/.profile/
web_data/downloads/results.csv 都不在白名单里，自然被排除。
"""
import shutil
import sys
from pathlib import Path

# 只把运行所需的顶层项拷进 app/
APP_INCLUDE = ("paperdl", "tests", "scripts", "pyproject.toml", "requirements.txt")
# 树内仍要跳过的
_SKIP_NAMES = {"__pycache__", ".pytest_cache"}
_SKIP_SUFFIX = {".pyc"}


def _scrub_copy(src_root: Path, dst_root: Path) -> None:
    for src in src_root.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)
        if any(part in _SKIP_NAMES for part in rel.parts):
            continue
        if src.suffix in _SKIP_SUFFIX:
            continue
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def build_app(repo: Path, app_dest: Path) -> None:
    app_dest.mkdir(parents=True, exist_ok=True)
    for item in APP_INCLUDE:
        src = repo / item
        if not src.exists():
            continue
        if src.is_dir():
            _scrub_copy(src, app_dest / item)
        else:
            shutil.copy2(src, app_dest / item)


def build_skill(repo: Path, dest: Path) -> None:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    build_app(repo, dest / "app")
    skilldir = repo / "skill"
    for name in ("SKILL.md", "AGENTS.md"):
        src = skilldir / name
        if src.exists():
            shutil.copy2(src, dest / name)
    refs = skilldir / "references"
    if refs.exists():
        shutil.copytree(refs, dest / "references", dirs_exist_ok=True)


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    dest = (Path(sys.argv[1]).expanduser() if len(sys.argv) > 1
            else Path.home() / ".claude" / "skills" / "paperdl")
    build_skill(repo, dest)
    print(f"已生成 skill 到 {dest}")
