import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Optional

_ITER = 200_000
SESSION_TTL = 7 * 24 * 3600  # 7天


def hash_password(password: str, salt: str = "") -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITER)
    return "%s$%s" % (salt, dk.hex())


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


class Auth:
    def __init__(self, base: Optional[Path] = None):
        self.base = Path(base) if base else Path.cwd()
        self.dir = self.base / "web_data"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.users_path = self.dir / "users.json"
        self.sessions_path = self.dir / "sessions.json"
        self.users = self._load(self.users_path)       # username -> {"pw": stored, "created": ts}
        self.sessions = self._load(self.sessions_path)  # sid -> {"user": u, "exp": ts}

    def _load(self, p: Path) -> dict:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self, p: Path, data: dict):
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def register(self, username: str, password: str) -> tuple:
        username = (username or "").strip()
        if not username or not password:
            return (False, "用户名和密码不能为空")
        if len(password) < 6:
            return (False, "密码至少 6 位")
        if username in self.users:
            return (False, "用户名已存在")
        self.users[username] = {"pw": hash_password(password), "created": int(time.time())}
        self._save(self.users_path, self.users)
        return (True, "")

    def login(self, username: str, password: str) -> Optional[str]:
        u = self.users.get((username or "").strip())
        if not u or not verify_password(password or "", u["pw"]):
            return None
        sid = secrets.token_urlsafe(32)
        self.sessions[sid] = {"user": username.strip(), "exp": int(time.time()) + SESSION_TTL}
        self._save(self.sessions_path, self.sessions)
        return sid

    def user_for_sid(self, sid: Optional[str]) -> Optional[str]:
        if not sid:
            return None
        s = self.sessions.get(sid)
        if not s:
            return None
        if s.get("exp", 0) < int(time.time()):
            self.sessions.pop(sid, None)
            self._save(self.sessions_path, self.sessions)
            return None
        return s["user"]

    def logout(self, sid: Optional[str]):
        if sid and sid in self.sessions:
            self.sessions.pop(sid, None)
            self._save(self.sessions_path, self.sessions)
