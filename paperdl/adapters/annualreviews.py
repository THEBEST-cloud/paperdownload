"""Annual Reviews (10.1146) 适配器。

annualreviews.org 走中科院通行证 Shibboleth(入口 annualreviews.org/session/ext/shib)拿机构
授权，patchright 过 Cloudflare。/doi/pdf/{doi}?download=true 触发下载，用"导航+捕获"取裸 PDF。
会话由 downloader.ensure_shib_session 对 'annualreviews' 建立。"""
from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata
from paperdl.session import capture_pdf_download

key = "annualreviews"


def article_url(doi: str) -> str:
    return "https://www.annualreviews.org/doi/" + doi


def pdf_url(doi: str) -> str:
    return "https://www.annualreviews.org/doi/pdf/" + doi + "?download=true"


def download(page, md: Metadata) -> DownloadResult:
    # 文章页：过 Cloudflare、建立 referer(机构会话已由 Shibboleth 建好)
    try:
        page.goto(article_url(md.doi), wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    for _ in range(12):  # 等 patchright 过 Cloudflare "Just a moment"
        try:
            if "just a moment" not in (page.title() or "").lower():
                break
        except Exception:
            pass
        page.wait_for_timeout(2500)
    # 导航到 Download PDF 链接 → Chrome 下载 → 捕获字节
    data = capture_pdf_download(page, pdf_url(md.doi))
    if data:
        return DownloadResult(ok=True, pdf_bytes=data)
    return DownloadResult(ok=False, reason="no_access")
