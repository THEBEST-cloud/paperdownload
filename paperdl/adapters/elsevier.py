import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.credentials import load_env
from paperdl.resolver import Metadata

key = "elsevier"
API = "https://api.elsevier.com/content/article/doi/"


def build_headers(api_key: str, insttoken: str = "") -> dict:
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/pdf"}
    if insttoken:
        headers["X-ELS-Insttoken"] = insttoken
    return headers


def classify_response(status: int, body: bytes) -> DownloadResult:
    if status == 200:
        if body[:5].startswith(b"%PDF"):
            return DownloadResult(ok=True, pdf_bytes=body)
        # 200 但不是 PDF：通常是全文 XML 或 abstract，无 PDF 权限/不提供
        return DownloadResult(ok=False, reason="no_pdf")
    if status in (401, 403):
        return DownloadResult(ok=False, reason="no_access")
    return DownloadResult(ok=False, reason="error")


def download(page, md: Metadata) -> DownloadResult:
    cfg = load_env()
    api_key = cfg.get("ELSEVIER_API_KEY")
    if not api_key:
        return DownloadResult(ok=False, reason="no_api_key")
    headers = build_headers(api_key, cfg.get("ELSEVIER_INSTTOKEN", "") or "")
    try:
        # trust_env=False 确保直连(忽略本机代理)，用机构 IP
        with httpx.Client(timeout=120, follow_redirects=True, trust_env=False) as c:
            r = c.get(API + md.doi, headers=headers)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    return classify_response(r.status_code, r.content)
