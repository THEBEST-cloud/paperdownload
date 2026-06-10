"""PNAS (10.1073) 适配器。

PNAS 在 pnas.org(Atypon 平台)。很多文章开放获取(尤其早于半年的)，但 PDF 端点被 Cloudflare
挡住，httpx/Unpaywall 兜底取不到。用 patchright 浏览器过 Cloudflare，再导航到 Download PDF
链接(?download=true)触发下载并捕获。las 上没有 PNAS 的 Shibboleth 入口，故只覆盖 OA/可直取的文章。"""
from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata
from paperdl.session import capture_pdf_download

key = "pnas"


def article_url(doi: str) -> str:
    return "https://www.pnas.org/doi/" + doi


def pdf_url(doi: str) -> str:
    return "https://www.pnas.org/doi/pdf/" + doi + "?download=true"


def download(page, md: Metadata) -> DownloadResult:
    # 文章页：过 Cloudflare、建立 referer
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
    # 拿不到：多半是未开放/订阅墙(本机无机构 IP、无 PNAS 联邦入口)
    return DownloadResult(ok=False, reason="no_access")
