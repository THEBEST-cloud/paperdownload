import re
from typing import Optional

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "ieee"

_ARNUM = re.compile(r"/document/(\d+)")


def arnumber(url: str) -> Optional[str]:
    """从 IEEE Xplore 文章 URL(/document/<arnumber>) 提取 arnumber。"""
    m = _ARNUM.search(url or "")
    return m.group(1) if m else None


def getpdf_url(arn: str) -> str:
    return "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=" + arn


def download(page, md: Metadata) -> DownloadResult:
    # 机构会话(Shibboleth)由下载流程在首篇 IEEE 前建立；这里导航到文章页取 arnumber 再下 PDF。
    try:
        page.goto(md.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    page.wait_for_timeout(2000)
    arn = arnumber(page.url)
    if not arn:
        if "login" in page.url.lower() or "shibboleth" in page.url.lower():
            return DownloadResult(ok=False, reason="no_access")
        return DownloadResult(ok=False, reason="no_pdf")
    try:
        resp = page.request.get(getpdf_url(arn), headers={"Referer": page.url}, timeout=120000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if resp.status != 200:
        return DownloadResult(ok=False, reason="no_access")
    body = resp.body()
    if not body[:5].startswith(b"%PDF"):
        return DownloadResult(ok=False, reason="blocked")
    return DownloadResult(ok=True, pdf_bytes=body)
