from typing import Optional

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "rsc"


def pdf_url_from_landing(landing_url: str) -> Optional[str]:
    base = landing_url.split("?")[0].split("#")[0]
    if "/articlelanding/" in base:
        return base.replace("/articlelanding/", "/articlepdf/")
    return None


def download(page, md: Metadata) -> DownloadResult:
    try:
        page.goto(md.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    pdf_url = pdf_url_from_landing(page.url)
    if not pdf_url:
        if "login" in page.url.lower() or "shibboleth" in page.url.lower():
            return DownloadResult(ok=False, reason="no_access")
        return DownloadResult(ok=False, reason="no_pdf")
    try:
        resp = page.request.get(pdf_url, headers={"Referer": page.url}, timeout=120000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if resp.status != 200:
        return DownloadResult(ok=False, reason="no_access")
    body = resp.body()
    if not body[:5].startswith(b"%PDF"):
        return DownloadResult(ok=False, reason="blocked")
    return DownloadResult(ok=True, pdf_bytes=body)
