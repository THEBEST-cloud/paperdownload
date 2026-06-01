import re
from typing import Optional
from urllib.parse import urljoin

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "nature"

_CIT = re.compile(r'name="citation_pdf_url"[^>]*content="([^"]+)"', re.I)
_CIT2 = re.compile(r'content="([^"]+)"[^>]*name="citation_pdf_url"', re.I)
_ARTICLE = re.compile(r"/articles/[^/?#]+$")


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
        return DownloadResult(ok=False, reason="blocked")
    return DownloadResult(ok=True, pdf_bytes=body)
