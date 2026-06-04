import re
from typing import Optional

from paperdl.session import LAS_HOME, auto_login

# 出版商 -> 用于在 las 入口 URL 中识别该出版商的关键串
# 适配器 key -> Shibboleth 入口 key：这些浏览器型出版商靠机构联邦会话取订阅全文。
# 下载主流程会在首次遇到该出版商时建立一次会话(有头-Xvfb)，之后复用。
ADAPTER_ENTRY = {
    "nature": "nature",
    "acs": "acs",
    "ieee": "ieee",
}

ENTRY_MATCH = {
    "nature": "sp.nature.com/saml",
    "springer": "fsso.springer.com",
    "science": "targetSP=https%3A%2F%2Fwww.science.org",
    "acm": "targetSP=https%3A%2F%2Fdl.acm.org",
    "wiley_web": "onlinelibrary.wiley.com",
    "elsevier_web": "auth.elsevier.com/ShibAuth",
    "ieee": "ieeexplore.ieee.org/servlet/wayf",
    "acs": "pubs.acs.org",
}

_CONSENT_SUBMIT = """() => {
  const b=document.querySelector("[name='_eventId_proceed']"); const f=(b&&b.form)||document.forms[0];
  if(!f) return 'NOFORM';
  if(!f.querySelector("[name='_eventId_proceed']")){const h=document.createElement('input');h.type='hidden';h.name='_eventId_proceed';h.value='1';f.appendChild(h);}
  f.submit(); return 'OK';
}"""


def fetch_entries(page) -> dict:
    """打开 las 文献获取页，抓取所有 getInUrl(...) 的 Shibboleth 入口，按 ENTRY_MATCH 归类。返回 {publisher: url}。"""
    page.goto(LAS_HOME, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(2500)
    oncs = page.eval_on_selector_all(
        "a", "els=>els.map(e=>e.getAttribute('onclick')||'').filter(s=>s.indexOf('getInUrl')>=0)")
    urls = []
    for o in oncs:
        m = re.search(r"getInUrl\('([^']+)'", o)
        if m:
            urls.append(m.group(1).replace("&amp;", "&"))
    out = {}
    for pub, needle in ENTRY_MATCH.items():
        for u in urls:
            if needle in u:
                out[pub] = u
                break
    return out


def _safe(fn, default=""):
    """页面跳转中途调用 title()/content()/query_selector 会抛错；包一层当作'还在跳转'。"""
    try:
        return fn()
    except Exception:
        return default


def ensure_session(page, entry_url: str, cid: str, pw: str) -> bool:
    """走出版商 Shibboleth 入口建立已认证会话(OAuth 自动 SSO + 同意页原生提交)。成功返回 True。"""
    auto_login(page, cid, pw, timeout=45000)
    page.goto(entry_url, wait_until="domcontentloaded", timeout=60000)
    # 等 OAuth iframe 自动 SSO
    for _ in range(20):
        page.wait_for_timeout(2000)
        t = _safe(page.title)
        u = _safe(lambda: page.url)
        if "Information Release" in t:
            break
        if u and "passport.escience.cn/idp" not in u:
            break
        if "Uncaught" in t:
            return False
    # 同意页 / SAML 中转
    for _ in range(5):
        t = _safe(page.title)
        proceed = _safe(lambda: page.query_selector("[name='_eventId_proceed']"), None)
        c = _safe(page.content)
        if "Information Release" in t or proceed:
            _safe(lambda: page.evaluate(_CONSENT_SUBMIT), None)
            page.wait_for_timeout(3500)
        elif "SAMLResponse" in c:
            sb = _safe(lambda: page.query_selector("input[type=submit],button[type=submit]"), None)
            if sb:
                _safe(sb.click, None)
            page.wait_for_timeout(2500)
        else:
            break
    return "passport.escience.cn/idp" not in _safe(lambda: page.url, "")
