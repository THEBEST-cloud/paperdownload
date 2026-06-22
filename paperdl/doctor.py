"""一键自检：依赖/chromium/xvfb/.paperdl.env/代理/登录态。"""
import importlib.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Check:
    name: str
    status: str  # "ok" | "warn" | "fail"
    detail: str


def check_deps() -> Check:
    missing = [m for m in ("patchright", "httpx", "fastapi", "uvicorn")
               if importlib.util.find_spec(m) is None]
    if missing:
        return Check("Python 依赖", "fail", "缺少: " + ", ".join(missing) + "（跑 scripts/setup.sh）")
    return Check("Python 依赖", "ok", "patchright/httpx/fastapi/uvicorn 已装")


def check_chromium() -> Check:
    try:
        from patchright.sync_api import sync_playwright
        p = sync_playwright().start()
        try:
            exe = p.chromium.executable_path
        finally:
            p.stop()
        if exe and Path(exe).exists():
            return Check("patchright chromium", "ok", exe)
        return Check("patchright chromium", "fail", "未安装（patchright install chromium）")
    except Exception as e:
        return Check("patchright chromium", "fail", str(e)[:70])


def check_xvfb() -> Check:
    path = shutil.which("Xvfb")
    if path:
        return Check("Xvfb", "ok", path)
    return Check("Xvfb", "fail", "未安装（sudo apt install -y xvfb）")


def check_env(base: Path) -> Check:
    from paperdl.configure import parse_env
    p = Path(base) / ".paperdl.env"
    if not p.exists():
        return Check(".paperdl.env", "fail", "不存在（跑 paperdl config）")
    d = parse_env(p.read_text(encoding="utf-8"))
    missing = [k for k in ("CSTCLOUD_ID", "CSTCLOUD_PASSWORD") if not d.get(k)]
    if missing:
        return Check(".paperdl.env", "fail", "缺必填: " + ", ".join(missing))
    return Check(".paperdl.env", "ok", "通行证账号已配")


def check_proxy_env(environ: Optional[dict] = None) -> Check:
    environ = environ if environ is not None else os.environ
    leaked = sorted({v.lower() for v in ("http_proxy", "https_proxy", "all_proxy",
                                         "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
                     if environ.get(v)})
    if leaked:
        return Check("代理环境变量", "warn",
                     "检测到 " + ",".join(leaked) +
                     "：会让浏览器走境外、破坏通行证/Shibboleth 登录，建议 unset")
    return Check("代理环境变量", "ok", "无代理泄漏（机构访问靠 Shibboleth 非 IP）")


def check_login(base: Path) -> Check:
    prof = Path(base) / ".profile"
    if prof.exists() and any(prof.iterdir()):
        return Check("登录态", "ok", ".profile 存在（约 10 天有效）")
    return Check("登录态", "warn", "未登录（跑 paperdl login 完成一次性短信验证）")


def run_doctor(base: Optional[Path] = None) -> int:
    base = Path(base) if base else Path.cwd()
    checks: List[Check] = [
        check_deps(), check_chromium(), check_xvfb(),
        check_env(base), check_proxy_env(), check_login(base),
    ]
    icon = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
    for c in checks:
        print(f"{icon[c.status]} {c.name}: {c.detail}")
    failed = sum(1 for c in checks if c.status == "fail")
    print("\n" + ("全部通过" if failed == 0 else f"{failed} 项需处理"))
    return 1 if failed else 0
