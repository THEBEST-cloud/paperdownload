import os
import re
import subprocess
import tempfile

import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.credentials import load_env
from paperdl.resolver import Metadata

key = "elsevier"
API = "https://api.elsevier.com/content/article/doi/"
_PII = re.compile(r"/pii/([A-Z0-9]+)", re.I)


def build_headers(api_key: str, insttoken: str = "") -> dict:
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/pdf"}
    if insttoken:
        headers["X-ELS-Insttoken"] = insttoken
    return headers


def pdf_page_count(data: bytes) -> int:
    """用 pdfinfo 数页数；失败回退到原始字节里数 /Type/Page。拿不到返回 -1。"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            out = subprocess.run(["pdfinfo", path], capture_output=True,
                                 text=True, timeout=30)
            for line in out.stdout.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split()[1])
        finally:
            os.unlink(path)
    except Exception:
        pass
    # 回退：数页对象（对 Elsevier 的 1.4 预览 PDF 足够可靠）
    try:
        import re
        return len(re.findall(rb"/Type\s*/Page[^s]", data)) or -1
    except Exception:
        return -1


def classify_response(status: int, body: bytes, has_insttoken: bool = False) -> DownloadResult:
    if status == 200:
        if body[:5].startswith(b"%PDF"):
            # 无机构令牌时，订阅文章 API 只返回首页预览(正好 1 页)。
            # OA 文章会返回完整全文(>1 页)，照常通过。配了令牌则信任结果。
            if not has_insttoken and pdf_page_count(body) == 1:
                return DownloadResult(ok=False, reason="elsevier_preview")
            return DownloadResult(ok=True, pdf_bytes=body)
        # 200 但不是 PDF：通常是全文 XML 或 abstract，无 PDF 权限/不提供
        return DownloadResult(ok=False, reason="no_pdf")
    if status in (401, 403):
        return DownloadResult(ok=False, reason="no_access")
    return DownloadResult(ok=False, reason="error")


def _api_download(md: Metadata) -> DownloadResult:
    cfg = load_env()
    api_key = cfg.get("ELSEVIER_API_KEY")
    if not api_key:
        return DownloadResult(ok=False, reason="no_api_key")
    insttoken = cfg.get("ELSEVIER_INSTTOKEN", "") or ""
    headers = build_headers(api_key, insttoken)
    try:
        # trust_env=False 确保直连(忽略本机代理)
        with httpx.Client(timeout=120, follow_redirects=True, trust_env=False) as c:
            r = c.get(API + md.doi, headers=headers)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    return classify_response(r.status_code, r.content, has_insttoken=bool(insttoken))


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _browser_download(page, md: Metadata):
    """走 ScienceDirect 网页(已由 ensure_shib_session 建立机构会话)下订阅全文。
    流程：开文章页→取带 md5+pid 令牌的 View PDF 链接→导航触发下载(profile 已设
    always_open_pdf_externally)→捕获 download 事件读取裸 PDF。返回 bytes 或 None。"""
    def wait_cf():
        for _ in range(12):  # 等 patchright 过 Cloudflare
            if "just a moment" not in (_safe(page.title, "") or "").lower():
                break
            page.wait_for_timeout(2500)

    art = md.url or ("https://doi.org/" + md.doi)
    if not _safe(lambda: page.goto(art, wait_until="domcontentloaded", timeout=60000)):
        return None
    wait_cf()
    m = _PII.search(_safe(lambda: page.url, "") or "")
    if not m:
        return None
    pii = m.group(1)
    # doi.org 常落在 linkinghub.elsevier.com 中转页(无 View PDF 链接)；规范化到 SD 文章页
    if "sciencedirect.com/science/article/pii/" not in (_safe(lambda: page.url, "") or ""):
        if not _safe(lambda: page.goto(
                "https://www.sciencedirect.com/science/article/pii/" + pii,
                wait_until="domcontentloaded", timeout=60000)):
            return None
        wait_cf()
    # 轮询等 "View PDF" 链接渲染出来(带 md5+pid 令牌)；订阅文章才有，未订阅则一直没有
    href = None
    for _ in range(5):
        href = _safe(lambda: page.eval_on_selector_all(
            "a", "els=>{const a=els.find(e=>(e.href||'').includes('/%s/pdfft')); return a?a.href:null;}" % pii))
        if href:
            break
        page.wait_for_timeout(2000)
    if not href:
        return None
    # 导航到 View PDF 链接 → Chrome 直接下载 PDF → 捕获 download 事件取字节
    try:
        with page.expect_download(timeout=45000) as di:
            _safe(lambda: page.goto(href, timeout=20000))  # 触发下载会中断导航，正常
        data = open(di.value.path(), "rb").read()
    except Exception:
        return None
    if data and data[:5].startswith(b"%PDF"):
        return data
    return None


def download(page, md: Metadata) -> DownloadResult:
    # 1. 官方 API 先试：OA 文章直接拿全文；配了 insttoken 则订阅全文也走 API。
    res = _api_download(md)
    if res.ok:
        return res
    # 2. 订阅文章(API 只给预览/拒绝)：走 ScienceDirect 机构网页会话下全文。
    if page is not None and res.reason in ("elsevier_preview", "no_access", "no_pdf"):
        data = _browser_download(page, md)
        if data:
            return DownloadResult(ok=True, pdf_bytes=data)
    return res
