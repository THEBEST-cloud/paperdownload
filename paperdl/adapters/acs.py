from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "acs"


def pdf_url_for(doi: str) -> str:
    return "https://pubs.acs.org/doi/pdf/" + doi


def download(page, md: Metadata) -> DownloadResult:
    # 先访问文章页建立会话/referer，再取确定性的 PDF 链接
    try:
        page.goto(md.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if "login" in page.url.lower() or "shibboleth" in page.url.lower():
        return DownloadResult(ok=False, reason="no_access")
    try:
        resp = page.request.get(pdf_url_for(md.doi), timeout=120000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if resp.status != 200:
        return DownloadResult(ok=False, reason="no_access")
    body = resp.body()
    if not body[:5].startswith(b"%PDF"):
        return DownloadResult(ok=False, reason="blocked")
    return DownloadResult(ok=True, pdf_bytes=body)
