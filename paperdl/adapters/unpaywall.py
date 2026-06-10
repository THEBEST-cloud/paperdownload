"""Unpaywall 开放获取(OA)兜底适配器。

不少订阅文章(尤其 Elsevier/Wiley/Springer)有作者接收稿的免费 OA 版存在机构仓储/预印本里，
Unpaywall 收录了这些 OA 位置。当主适配器(订阅/API)失败或只拿到预览时，用它兜底捞 OA 全文。
合法、零鉴权、走直连(OA 不需要机构 IP)。来源：用户 hydro-case 的 bulk_fetch 思路。"""
import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "unpaywall"
API = "https://api.unpaywall.org/v2/"
EMAIL = "research@local"  # Unpaywall 要求带 email 参数
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def oa_pdf_urls(data: dict) -> list:
    """从 Unpaywall 响应里按优先级抽 OA PDF 链接(best_oa_location 优先，再各 oa_locations，去重)。"""
    urls = []
    best = data.get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        urls.append(best["url_for_pdf"])
    for loc in data.get("oa_locations") or []:
        u = loc.get("url_for_pdf") or loc.get("url")
        if u and u not in urls:
            urls.append(u)
    return urls


def download(page, md: Metadata) -> DownloadResult:
    # 走直连(trust_env=False)：OA 仓储是公开资源，不需机构 IP，与其余适配器一致不吃本机代理。
    headers = {"User-Agent": BROWSER_UA, "Accept": "application/pdf,*/*"}
    try:
        with httpx.Client(timeout=60, follow_redirects=True, trust_env=False) as c:
            r = c.get(API + md.doi, params={"email": EMAIL},
                      headers={"User-Agent": BROWSER_UA})
            if r.status_code != 200:
                return DownloadResult(ok=False, reason="no_oa")
            urls = oa_pdf_urls(r.json())
            if not urls:
                return DownloadResult(ok=False, reason="no_oa")
            for u in urls:
                try:
                    pr = c.get(u, headers=headers)
                except Exception:
                    continue
                body = pr.content
                if pr.status_code == 200 and body[:5].startswith(b"%PDF"):
                    return DownloadResult(ok=True, pdf_bytes=body)
    except Exception:
        return DownloadResult(ok=False, reason="no_oa")
    return DownloadResult(ok=False, reason="no_oa")
