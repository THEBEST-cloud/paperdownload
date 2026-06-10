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
    "elsevier": "elsevier_web",
    "science": "science",
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

# IdP 中转有时是一个自动提交的 SAMLResponse 表单(无同意按钮)；原生提交它继续跳转。
_AUTOPOST_SUBMIT = """() => {
  const f=document.querySelector("form");
  if(f && document.querySelector("input[name='SAMLResponse'],input[name='RelayState']")){f.submit();return 'POST';}
  return 'NO';
}"""

# 这些域名/路径是 SSO 中转态，需继续等待(不是终态)。Atypon(ACS/Science/ACM)的同意分两步
# (e1s1/e1s2)，每步都要原生提交 _eventId_proceed，全程可能经过多个中转 URL。
_RELAY_MARKERS = ("passport.escience.cn/idp", "action/ssostart", "/idp/",
                  "shibboleth.sso", "deliverinstcredentials", "authenticatesharedsp",
                  "/user/router/shib", "/saml", "wayf", "openathens", "federation/init",
                  # Elsevier 联邦登录最后还要过 id.elsevier.com 的 OAuth 授权中转才落 ScienceDirect
                  "id.elsevier.com", "authorization.oauth2")


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


def _is_relay(url: str) -> bool:
    u = (url or "").lower()
    return any(m in u for m in _RELAY_MARKERS)


def ensure_session(page, entry_url: str, cid: str, pw: str) -> bool:
    """走出版商 Shibboleth 入口建立已认证会话。成功(落到出版商域名)返回 True。

    通用流程，覆盖 SpringerLink / Nature / Elsevier(ShibAuth) / Atypon(ACS/Science/ACM,
    两步同意 e1s1+e1s2) / IEEE 等：①auto_login 建 portal 会话 ②走入口 ③循环：发现同意按钮
    (_eventId_proceed)就原生提交；在 IdP 上无按钮则提交自动 POST 表单(SAMLResponse)；仍在
    任意中转态则继续等；落到真实出版商域名即完成。
    """
    auto_login(page, cid, pw, timeout=45000)
    page.goto(entry_url, wait_until="domcontentloaded", timeout=60000)
    for _ in range(24):
        page.wait_for_timeout(1800)
        u = _safe(lambda: page.url)
        if "Uncaught" in _safe(page.title):
            return False
        proceed = _safe(lambda: page.query_selector("[name='_eventId_proceed']"), None)
        if proceed:
            _safe(lambda: page.evaluate(_CONSENT_SUBMIT), None)
            continue
        if "passport.escience.cn/idp" in (u or ""):
            # IdP 上但没有同意按钮 → 可能是自动提交的 SAMLResponse 中转表单
            _safe(lambda: page.evaluate(_AUTOPOST_SUBMIT), None)
            continue
        if _is_relay(u):
            continue  # 其它中转态(ssostart/router/shib 等)，继续等跳转
        break  # 落到真实出版商域名
    return not _is_relay(_safe(lambda: page.url, ""))
