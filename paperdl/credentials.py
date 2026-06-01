import os
from pathlib import Path
from typing import Optional, Tuple

ENV_FILE = ".paperdl.env"


def _parse_env_file(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        data[key.strip()] = value
    return data


def load_env(base: Optional[Path] = None) -> dict:
    """返回 .paperdl.env 文件值与环境变量合并的配置(环境变量优先)。"""
    base = Path(base) if base else Path.cwd()
    cfg = dict(_parse_env_file(base / ENV_FILE))
    for k in list(cfg.keys()):
        if k in os.environ:
            cfg[k] = os.environ[k]
    # 也纳入文件里没有但环境里有的相关键
    for k in ("ELSEVIER_API_KEY", "ELSEVIER_INSTTOKEN"):
        if k in os.environ:
            cfg[k] = os.environ[k]
    return cfg


def load_credentials(base: Optional[Path] = None) -> Optional[Tuple[str, str]]:
    base = Path(base) if base else Path.cwd()
    from_file = _parse_env_file(base / ENV_FILE)
    cid = os.environ.get("CSTCLOUD_ID") or from_file.get("CSTCLOUD_ID")
    pw = os.environ.get("CSTCLOUD_PASSWORD") or from_file.get("CSTCLOUD_PASSWORD")
    if cid and pw:
        return (cid, pw)
    return None
