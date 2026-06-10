import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

# patchright 是 Playwright 的隐身分支：运行时打掉 CDP 暴露的自动化痕迹，配合真实 Chrome
# 能过 Cloudflare 的 "Just a moment" 挑战(ScienceDirect/ACS/Science 等)。API 与 playwright 完全兼容。
from patchright.sync_api import sync_playwright

from paperdl.credentials import load_credentials

# 本机可能配了走境外的本地代理(如 127.0.0.1:7897)。CAS 通行证/机构全文必须用
# 机器真实国内 IP，否则被当境外陌生设备拦截、短信不达、全文权限认不出。
_PROXY_ENV_VARS = ("http_proxy", "https_proxy", "all_proxy", "ftp_proxy", "no_proxy",
                   "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "FTP_PROXY", "NO_PROXY")


def disable_proxy() -> None:
    """清掉本进程的代理环境变量，让 Chromium 与 httpx 都走直连。"""
    for var in _PROXY_ENV_VARS:
        os.environ.pop(var, None)


# 无头 Chromium 默认 UA 含 "HeadlessChrome"，会被 ScienceDirect 等反爬直接拦截。
# 用普通桌面 Chrome UA 伪装。
DESKTOP_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

LAS_HOME = "https://www.las.ac.cn/front/dataCenter/literatureAcquisition"
PASSPORT_LOGIN = "https://passport.escience.cn/login"


def profile_dir(base: Optional[Path] = None) -> Path:
    base = Path(base) if base else Path.cwd()
    return base / ".profile"


def _ensure_pdf_download_pref(pdir: Path) -> None:
    """让 Chrome 直接下载 PDF 而非内嵌渲染。Elsevier 走 ScienceDirect 时要靠"导航到 PDF→
    触发下载"来捕获字节(签名 URL 跨域、单次有效，截获+fetch 都不稳)。对其它适配器无影响
    (它们用 page.request/httpx/页内 fetch，不靠导航渲染)。"""
    import json
    pref = pdir / "Default" / "Preferences"
    try:
        pref.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(pref.read_text()) if pref.exists() else {}
        data.setdefault("plugins", {})["always_open_pdf_externally"] = True
        data.setdefault("download", {})["prompt_for_download"] = False
        pref.write_text(json.dumps(data))
    except Exception:
        pass


# 在页面里用浏览器自身的 fetch 取二进制并转 base64。
# 关键：page.request(Node 侧)的 TLS 指纹与浏览器不同，Cloudflare 会对其 cf_clearance 报 403；
# 而页内 fetch 走浏览器栈，指纹+cf_clearance 一致，能过。用于 Atypon(ACS/Science 等)取 PDF。
_FETCH_B64_JS = """async (url) => {
  try {
    const resp = await fetch(url, {credentials:'include'});
    const buf = await resp.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let bin=''; const C=0x8000;
    for(let i=0;i<bytes.length;i+=C){ bin+=String.fromCharCode.apply(null, bytes.subarray(i,i+C)); }
    return {status:resp.status, ct:(resp.headers.get('content-type')||''), b64:btoa(bin)};
  } catch(e) { return {status:0, ct:'', b64:'', err:String(e)}; }
}"""


def fetch_bytes_in_page(page, url: str):
    """通过当前页面的浏览器上下文 fetch(url)，返回 (status, content_type, bytes)。失败 bytes 为 None。"""
    import base64
    res = page.evaluate(_FETCH_B64_JS, url)
    b64 = res.get("b64") or ""
    data = base64.b64decode(b64) if b64 else None
    return res.get("status", 0), res.get("ct", ""), data


def capture_pdf_download(page, url: str, timeout: int = 45000):
    """导航到一个会触发 PDF 下载的 URL(profile 已设 always_open_pdf_externally，PDF 直接下载
    而非内嵌渲染)，捕获 download 事件并返回 PDF 字节。拿不到 PDF 返回 None。
    用于 Atypon 的 ePDF/签名跳转链(Science/Elsevier 等)，绕开跨域 fetch 与签名 URL 捕获。"""
    try:
        with page.expect_download(timeout=timeout) as di:
            try:
                page.goto(url, timeout=20000)  # 触发下载会中断导航，正常
            except Exception:
                pass
        data = open(di.value.path(), "rb").read()
        return data if data[:5].startswith(b"%PDF") else None
    except Exception:
        return None


@contextmanager
def browser_context(headless: bool, base: Optional[Path] = None, headed_xvfb: bool = False):
    """打开持久化上下文：登录态(cookie/localStorage)保存在 .profile/ 里复用。
    headed_xvfb=True 时，自动启动(或复用) Xvfb 虚拟显示器并以有头模式启动浏览器。"""
    if headed_xvfb:
        from paperdl.xvfb import ensure_display
        ensure_display()
        headless = False
    pdir = profile_dir(base)
    pdir.mkdir(parents=True, exist_ok=True)
    _ensure_pdf_download_pref(pdir)  # 让 PDF 走下载而非内嵌渲染(Elsevier 取全文用)
    disable_proxy()  # 进程级清代理，确保 Chrome 子进程不继承(代理走境外会被反爬/通行证拦)
    with sync_playwright() as pw:
        # 用 patchright 自带的 patched Chromium(不设 channel)：既能过 Cloudflare 的隐身，
        # 又与既有 .profile(playwright Chromium 所建)同源兼容，保住免短信的受信任登录态。
        # 不要覆盖 user_agent / 加 --disable-blink-features 等参数——会削弱 patchright 隐身。
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(pdir),
            headless=headless,
            no_viewport=True,
            accept_downloads=True,
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
