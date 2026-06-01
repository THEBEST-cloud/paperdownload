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


def load_credentials(base: Optional[Path] = None) -> Optional[Tuple[str, str]]:
    base = Path(base) if base else Path.cwd()
    from_file = _parse_env_file(base / ENV_FILE)
    cid = os.environ.get("CSTCLOUD_ID") or from_file.get("CSTCLOUD_ID")
    pw = os.environ.get("CSTCLOUD_PASSWORD") or from_file.get("CSTCLOUD_PASSWORD")
    if cid and pw:
        return (cid, pw)
    return None
