import re

import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.credentials import load_env
from paperdl.resolver import Metadata
from paperdl.session import capture_pdf_download

key = "wiley"
API = "https://api.wiley.com/onlinelibrary/tdm/v1/articles/"
_HOST = re.compile(r"^(https?://[^/]+)")


def build_headers(token: str) -> dict:
    return {"Wiley-TDM-Client-Token": token, "Accept": "application/pdf"}


def classify_response(status: int, body: bytes) -> DownloadResult:
    if status == 200:
        if body[:5].startswith(b"%PDF"):
            return DownloadResult(ok=True, pdf_bytes=body)
        return DownloadResult(ok=False, reason="no_pdf")
    if status in (401, 403):
        return DownloadResult(ok=False, reason="no_access")
    return DownloadResult(ok=False, reason="error")


def _api_download(md: Metadata) -> DownloadResult:
    token = load_env().get("WILEY_TDM_TOKEN")
    if not token:
        return DownloadResult(ok=False, reason="no_api_key")
    try:
        with httpx.Client(timeout=180, follow_redirects=True, trust_env=False) as c:
            r = c.get(API + md.doi, headers=build_headers(token))
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    return classify_response(r.status_code, r.content)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _browser_download(page, md: Metadata):
    """TDM 没授权时，走 Wiley OnlineLibrary 机构会话(已由 ensure_shib_session 建立)下全文。
    文章常重定向到学会子域(如 esajournals.onlinelibrary.wiley.com)；用该域的 /doi/pdfdirect/
    {doi}?download=true 触发下载并捕获(/doi/pdf 是 ePDF 阅读器，取不到)。"""
    art = "https://onlinelibrary.wiley.com/doi/" + md.doi
    if not _safe(lambda: page.goto(art, wait_until="domcontentloaded", timeout=60000)):
        return None
    for _ in range(12):  # 等 patchright 过 Cloudflare
        if "just a moment" not in (_safe(page.title, "") or "").lower():
            break
        page.wait_for_timeout(2500)
    m = _HOST.match(_safe(lambda: page.url, "") or "")
    base = m.group(1) if m else "https://onlinelibrary.wiley.com"
    return capture_pdf_download(page, base + "/doi/pdfdirect/" + md.doi + "?download=true")


def download(page, md: Metadata) -> DownloadResult:
    # 1. 官方 TDM API 先试(覆盖授权内的文章/OA)
    res = _api_download(md)
    if res.ok:
        return res
    # 2. TDM 没授权：走 OnlineLibrary 机构网页会话下全文
    if page is not None and res.reason in ("no_access", "no_pdf", "error"):
        data = _browser_download(page, md)
        if data:
            return DownloadResult(ok=True, pdf_bytes=data)
    return res
