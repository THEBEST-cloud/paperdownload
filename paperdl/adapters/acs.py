from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata
from paperdl.session import fetch_bytes_in_page

key = "acs"


def pdf_url_for(doi: str) -> str:
    return "https://pubs.acs.org/doi/pdf/" + doi


def download(page, md: Metadata) -> DownloadResult:
    # 先访问文章页：建立 referer + 让 patchright 过 Cloudflare "Just a moment" 挑战
    try:
        page.goto(md.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    # 等 Cloudflare JS 挑战自解(patchright 能过；最多等 ~30s)
    for _ in range(12):
        try:
            if "just a moment" not in (page.title() or "").lower():
                break
        except Exception:
            pass
        page.wait_for_timeout(2500)
    if "login" in page.url.lower() or "shibboleth" in page.url.lower():
        return DownloadResult(ok=False, reason="no_access")
    # Atypon: /doi/pdf/{doi} 返回裸 PDF。用页内 fetch(浏览器指纹+cf_clearance)避免 Cloudflare 403。
    try:
        status, ct, body = fetch_bytes_in_page(page, pdf_url_for(md.doi))
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if status != 200:
        return DownloadResult(ok=False, reason="no_access")
    if not body or not body[:5].startswith(b"%PDF"):
        # 200 但非 PDF：通常是 Cloudflare 挑战页或未授权的文章 HTML
        return DownloadResult(ok=False, reason="blocked")
    return DownloadResult(ok=True, pdf_bytes=body)
