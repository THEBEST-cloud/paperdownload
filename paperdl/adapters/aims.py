"""AIMS Press (10.3934) 适配器。

AIMS(American Institute of Mathematical Sciences)期刊多为开放获取，但 Crossref/Unpaywall
只给文章页链接、不给直接 PDF。PDF 真链形如 aimspress.com/aimspress-data/<刊>/<年>/<期>/PDF/
<file>.pdf，文件名从 DOI 推不出来，需从文章页抓。无 Cloudflare，纯 httpx 直取。"""
import re

import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "aims"
BASE = "https://www.aimspress.com"
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
_PDF = re.compile(r'href=["\']([^"\']*aimspress-data[^"\']*\.pdf)["\']', re.I)


def article_url(doi: str) -> str:
    return BASE + "/article/" + doi


def find_pdf_url(html: str):
    """从 AIMS 文章页 HTML 抓 PDF 真链(aimspress-data/.../*.pdf)。"""
    m = _PDF.search(html or "")
    if not m:
        return None
    u = m.group(1)
    if u.startswith("http"):
        return u
    return BASE + (u if u.startswith("/") else "/" + u)


def download(page, md: Metadata) -> DownloadResult:
    art = article_url(md.doi)
    try:
        with httpx.Client(timeout=60, follow_redirects=True, trust_env=False) as c:
            r = c.get(art, headers={"User-Agent": BROWSER_UA})
            if r.status_code != 200:
                return DownloadResult(ok=False, reason="no_access")
            pdf = find_pdf_url(r.text)
            if not pdf:
                return DownloadResult(ok=False, reason="no_pdf")
            pr = c.get(pdf, headers={"User-Agent": BROWSER_UA, "Referer": art})
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if pr.status_code == 200 and pr.content[:5].startswith(b"%PDF"):
        return DownloadResult(ok=True, pdf_bytes=pr.content)
    return DownloadResult(ok=False, reason="no_pdf")
