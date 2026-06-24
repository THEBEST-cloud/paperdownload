import re
from typing import Optional
from urllib.parse import urljoin

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "nature"

_CIT = re.compile(r'name="citation_pdf_url"[^>]*content="([^"]+)"', re.I)
_CIT2 = re.compile(r'content="([^"]+)"[^>]*name="citation_pdf_url"', re.I)
_ARTICLE = re.compile(r"/articles/[^/?#]+$")


# Cloudflare 反爬挑战页的特征（可重试），区别于 Nature 文章/付费墙 HTML（无订阅，终态）
_CF_MARKERS = ("just a moment", "cf-browser-verification", "challenge-platform", "_cf_chl")


def classify_non_pdf(body: bytes) -> str:
    """`.pdf` 端点返回的不是 PDF 时如何归类：
    - Cloudflare 挑战页 → blocked（疑似反爬，重试可能就好）
    - Nature 文章/付费墙 HTML → no_access（机构无订阅，终态，重试无用→馆际互借/NSTL）
    - 其它非 HTML 垃圾字节 → blocked
    """
    head = body[:6000].decode("utf-8", "ignore").lower()
    if any(m in head for m in _CF_MARKERS):
        return "blocked"
    if "<html" in head or "<!doctype html" in head:
        return "no_access"
    return "blocked"


def find_pdf_url(html: str, base_url: str) -> Optional[str]:
    for pat in (_CIT, _CIT2):
        m = pat.search(html or "")
        if m:
            return urljoin(base_url, m.group(1).replace("&amp;", "&"))
    # 回退：Nature 文章页 URL 直接加 .pdf
    path = base_url.split("?")[0].split("#")[0]
    if _ARTICLE.search(path):
        return path + ".pdf"
    return None


def download(page, md: Metadata) -> DownloadResult:
    try:
        page.goto(md.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    pdf_url = find_pdf_url(page.content(), page.url)
    if not pdf_url:
        if "login" in page.url.lower() or "shibboleth" in page.url.lower():
            return DownloadResult(ok=False, reason="no_access")
        return DownloadResult(ok=False, reason="no_pdf")
    try:
        resp = page.request.get(pdf_url, timeout=120000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if resp.status != 200:
        return DownloadResult(ok=False, reason="no_access")
    body = resp.body()
    if not body[:5].startswith(b"%PDF"):
        # 200 但不是 PDF：可能是 Cloudflare 挑战(可重试)或文章/付费墙 HTML(无订阅)
        return DownloadResult(ok=False, reason=classify_non_pdf(body))
    return DownloadResult(ok=True, pdf_bytes=body)
