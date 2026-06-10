"""Science / AAAS (10.1126) 适配器。

走中科院通行证 Shibboleth(Atypon, iam.atypon.com ssostart, targetSP=science.org)拿机构授权，
patchright 过 Cloudflare。Science 的 /doi/pdf 返回的是 ePDF 阅读器 HTML，但 ?download=true 会
触发真正下载，故用"导航触发下载 + 捕获"取裸 PDF(profile 已设 always_open_pdf_externally)。
会话由 downloader.ensure_shib_session 对 'science' 建立。"""
from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata
from paperdl.session import capture_pdf_download

key = "science"


def article_url(doi: str) -> str:
    return "https://www.science.org/doi/" + doi


def pdf_url(doi: str) -> str:
    return "https://www.science.org/doi/pdf/" + doi + "?download=true"


def download(page, md: Metadata) -> DownloadResult:
    # 1. 文章页：过 Cloudflare、建立 referer(机构会话已由 Shibboleth 建好)
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
    url = (page.url or "").lower()
    if "/action/login" in url or "signin" in url:
        return DownloadResult(ok=False, reason="no_access")
    # 2. 导航到 Download PDF 链接 → Chrome 下载 → 捕获字节
    data = capture_pdf_download(page, pdf_url(md.doi))
    if data:
        return DownloadResult(ok=True, pdf_bytes=data)
    # 没拿到：多半是会话没建好/未订阅，交给上层(可能重建会话重试)
    return DownloadResult(ok=False, reason="blocked")
