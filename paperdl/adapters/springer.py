import re
from urllib.parse import urljoin
from typing import Optional

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

# 不引入额外 HTML 解析依赖：用正则在 Springer 文章页定位下载链接。
# Springer 的下载链接形如 /content/pdf/<doi>.pdf，class 含 c-pdf-download__link。
_PDF_HREF = re.compile(
    r'href="(?P<href>[^"]*?/content/pdf/[^"]+\.pdf)"', re.IGNORECASE
)


def find_pdf_url(html: str, base_url: str) -> Optional[str]:
    m = _PDF_HREF.search(html)
    if not m:
        return None
    return urljoin(base_url, m.group("href"))


key = "springer"


def download(page, md: Metadata) -> DownloadResult:
    # md.url 是 dx.doi.org 链接；登录态下让浏览器自己解析到机构代理域。
    try:
        page.goto(md.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")

    html = page.content()
    pdf_url = find_pdf_url(html, base_url=page.url)
    if not pdf_url:
        # 页面里没有下载链接：可能无权限或反爬拦截
        if "login" in page.url.lower() or "shibboleth" in page.url.lower():
            return DownloadResult(ok=False, reason="no_access")
        return DownloadResult(ok=False, reason="no_pdf")

    # 用浏览器上下文的请求拿 PDF（带上登录 cookie）
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
