import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.credentials import load_env
from paperdl.resolver import Metadata

key = "wiley"
API = "https://api.wiley.com/onlinelibrary/tdm/v1/articles/"


def build_headers(token: str) -> dict:
    return {"Wiley-TDM-Client-Token": token, "Accept": "application/pdf"}


def classify_response(status: int, body: bytes) -> DownloadResult:
    if status == 200:
        if body[:5].startswith(b"%PDF"):
            return DownloadResult(ok=True, pdf_bytes=body)
        return DownloadResult(ok=False, reason="no_pdf")
    if status in (401, 403):
        return DownloadResult(ok=False, reason="no_access")
    return DownloadResult(ok=False, reason="error")


def download(page, md: Metadata) -> DownloadResult:
    token = load_env().get("WILEY_TDM_TOKEN")
    if not token:
        return DownloadResult(ok=False, reason="no_api_key")
    try:
        with httpx.Client(timeout=180, follow_redirects=True, trust_env=False) as c:
            r = c.get(API + md.doi, headers=build_headers(token))
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    return classify_response(r.status_code, r.content)
