from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

from paperdl.credentials import load_credentials

LAS_HOME = "https://www.las.ac.cn/front/dataCenter/literatureAcquisition"
PASSPORT_LOGIN = "https://passport.escience.cn/login"


def profile_dir(base: Optional[Path] = None) -> Path:
    base = Path(base) if base else Path.cwd()
    return base / ".profile"


@contextmanager
def browser_context(headless: bool, base: Optional[Path] = None):
    """打开持久化上下文：登录态(cookie/localStorage)保存在 .profile/ 里复用。"""
    pdir = profile_dir(base)
    pdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(pdir),
            headless=headless,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            yield ctx
        finally:
            ctx.close()


def auto_login(page, cstcloud_id: str, password: str, timeout: int = 30000) -> bool:
    """在中国科技云通行证登录页自动填账号密码并提交。
    返回 True 表示已登录（或本就已登录）；False 表示未确认成功（可能弹了验证码/二次验证，需人工）。"""
    page.goto(PASSPORT_LOGIN, wait_until="domcontentloaded", timeout=timeout)
    # 已登录时 /login 会重定向走，页面就没有密码框了
    if page.query_selector("#password") is None:
        return True
    page.fill("#username", cstcloud_id)
    page.fill("#password", password)
    try:
        page.check("#remember")
    except Exception:
        pass
    page.click("#loginBtn")
    try:
        # 登录成功后跳离 /login，密码框消失；若弹验证码则密码框还在 -> 超时返回 False
        page.wait_for_function("() => !document.querySelector('#password')", timeout=timeout)
        return True
    except Exception:
        return False


def run_login(base: Optional[Path] = None) -> None:
    """打开浏览器：有凭证则自动登录通行证；随后停在 las.ac.cn 供人工处理验证码/出版商机构登录。"""
    creds = load_credentials(base)
    with browser_context(headless=False, base=base) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if creds:
            print("检测到 .paperdl.env 凭证，尝试自动登录中国科技云通行证…")
            if auto_login(page, creds[0], creds[1]):
                print("✅ 自动登录成功（通行证会话已建立）。")
            else:
                print("⚠️ 自动登录未确认成功——可能弹了验证码或二次验证，请在浏览器窗口里手动完成登录。")
        else:
            print("未找到 .paperdl.env 凭证（或缺字段）。请在浏览器窗口里手动登录。")
        page.goto(LAS_HOME)
        print("如需在出版商站点做一次机构登录，请现在在浏览器里操作。")
        print("全部完成后回到终端按回车保存会话。")
        input("按回车结束登录并保存会话 > ")
