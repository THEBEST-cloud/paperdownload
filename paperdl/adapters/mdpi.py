"""MDPI (10.3390) 适配器。

MDPI 期刊全开放获取，但 mdpi.com 有反爬墙(httpx 403 Access Denied)。用 patchright 过墙，
文章页里的 "Download PDF" 链接形如 mdpi.com/<issn>/<vol>/<issue>/<num>/pdf?version=...
(version 从页面取，构造不出)，导航到它触发下载并捕获。无需机构登录。"""
import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata
from paperdl.session import capture_pdf_download

key = "mdpi"
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
# 匹配文章页里的 PDF 下载链接(.../pdf 或 .../pdf?version=...)
_FIND_PDF = ("els=>{const a=els.find(e=>/\\/pdf(\\?|$)/i.test(e.href||'')); return a?a.href:null;}")


def resolve_article_url(doi: str):
    """httpx 跟随 doi.org 拿 mdpi.com 文章 URL(即便 403 也能拿最终 URL)。"""
    try:
        with httpx.Client(timeout=25, follow_redirects=True, trust_env=False) as c:
            return str(c.get("https://doi.org/" + doi, headers={"User-Agent": BROWSER_UA}).url)
    except Exception:
        return None


def download(page, md: Metadata) -> DownloadResult:
    art = resolve_article_url(md.doi) or ("https://doi.org/" + md.doi)
    try:
        page.goto(art, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    for _ in range(12):  # 等 patchright 过反爬墙
        try:
            t = (page.title() or "").lower()
            if "just a moment" not in t and "access denied" not in t and t.strip():
                break
        except Exception:
            pass
        page.wait_for_timeout(2500)
    # 取 "Download PDF" 真链(带 version)
    href = None
    for _ in range(5):
        href = _safe(lambda: page.eval_on_selector_all("a", _FIND_PDF))
        if href:
            break
        page.wait_for_timeout(1500)
    if not href:
        return DownloadResult(ok=False, reason="no_pdf")
    data = capture_pdf_download(page, href)
    if data:
        return DownloadResult(ok=True, pdf_bytes=data)
    return DownloadResult(ok=False, reason="no_access")


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default
