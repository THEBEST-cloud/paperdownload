import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

from paperdl.credentials import load_credentials

# 本机可能配了走境外的本地代理(如 127.0.0.1:7897)。CAS 通行证/机构全文必须用
# 机器真实国内 IP，否则被当境外陌生设备拦截、短信不达、全文权限认不出。
_PROXY_ENV_VARS = ("http_proxy", "https_proxy", "all_proxy", "ftp_proxy", "no_proxy",
                   "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "FTP_PROXY", "NO_PROXY")


def disable_proxy() -> None:
    """清掉本进程的代理环境变量，让 Chromium 与 httpx 都走直连。"""
    for var in _PROXY_ENV_VARS:
        os.environ.pop(var, None)

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
    disable_proxy()  # 进程级清代理，确保 Chromium 子进程不继承
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(pdir),
            headless=headless,
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-proxy-server",  # 直连，忽略任何代理
            ],
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


def find_verification_frame(page):
    """新设备验证表单在页面里(可能在同源 iframe)。返回含 #phoneNumber 的 frame/page，找不到返回 None。"""
    candidates = [page]
    try:
        candidates += list(page.frames)
    except Exception:
        pass
    for fr in candidates:
        try:
            if fr.query_selector("#phoneNumber") is not None:
                return fr
        except Exception:
            continue
    return None


def needs_device_verification(page) -> bool:
    return find_verification_frame(page) is not None


# 直接调发送接口，绕过页面国际电话控件(intl-tel-input)的前端格式校验 bug：
# 该控件在境外/默认区号下会把合法国内号码判为格式错误而不发短信；服务器其实接受裸 11 位。
_SEND_SMS_JS = """(phone) => {
    const $ = window.jQuery;
    let r = null;
    $.ajax({url:'/user/phone/loginName/sendValidateCode?type=new',
            data:'phoneNum='+encodeURIComponent(phone), async:false,
            success:function(d){ r='OK '+JSON.stringify(d); },
            error:function(x){ r='ERR '+x.status; }});
    return r;
}"""

# 原生 submit 绕过 jQuery validate 的提交拦截，直接 POST 到 savePhone。
_SUBMIT_JS = """(a) => {
    document.querySelector('#phoneNumber').value = a.phone;
    document.querySelector('#validateCode').value = a.code;
    document.getElementById('createRequestForm').submit();
}"""


def complete_device_verification(page, input_fn=input) -> bool:
    """终端驱动一次性设备验证：问手机号 -> 直连接口发短信 -> 问短信码 -> 原生提交。
    成功(离开验证页)返回 True。"""
    frame = find_verification_frame(page)
    if frame is None:
        return False
    phone = input_fn("请输入接收短信的手机号(11位): ").strip()
    send = frame.evaluate(_SEND_SMS_JS, phone)
    print("已请求发送验证码:", send)
    code = input_fn("请输入收到的短信验证码: ").strip()
    frame.evaluate(_SUBMIT_JS, {"phone": phone, "code": code})
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception:
        pass
    try:
        page.wait_for_timeout(3000)
    except Exception:
        pass
    return find_verification_frame(page) is None


def run_login(base: Optional[Path] = None) -> None:
    """无头浏览器自动登录通行证；遇到新设备验证则在终端走一次性短信验证。"""
    creds = load_credentials(base)
    if not creds:
        print("未找到 .paperdl.env 凭证（或缺字段）。请先填好 .paperdl.env 再运行。")
        return
    with browser_context(headless=True, base=base) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        print("正在自动登录中国科技云通行证…")
        auto_login(page, creds[0], creds[1])
        if needs_device_verification(page):
            print("⚠️ 检测到新设备验证（绑定手机+短信）。这是首次在本机登录需要的一次性步骤。")
            ok = complete_device_verification(page)
            if ok:
                print("✅ 设备验证通过，会话已建立。")
            else:
                print("❌ 设备验证未通过（验证码错误/超时？）。请重试 python -m paperdl login。")
                return
        else:
            print("✅ 自动登录成功（本机已是受信任设备，无需验证）。")
        # 预热：访问 las.ac.cn 让 SSO 会话落到机构站点
        try:
            page.goto(LAS_HOME, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(2000)
        except Exception:
            pass
        print("会话已保存到 .profile/。现在可以运行：python -m paperdl run <清单.txt>")
