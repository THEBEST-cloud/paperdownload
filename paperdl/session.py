from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

LAS_HOME = "https://www.las.ac.cn/front/dataCenter/literatureAcquisition"


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


def run_login(base: Optional[Path] = None) -> None:
    """有头打开 las.ac.cn，提示用户手动完成通行证登录与出版商机构登录。"""
    with browser_context(headless=False, base=base) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(LAS_HOME)
        print("浏览器已打开。请在窗口中完成：")
        print("  1) 用中国科技云通行证登录（账号=中科院邮箱），处理验证码/二次验证；")
        print("  2) 点进 Springer（link.springer.com）做一次机构登录，确认能看到全文；")
        print("完成后回到终端按回车保存会话。")
        input("按回车结束登录并保存会话 > ")
