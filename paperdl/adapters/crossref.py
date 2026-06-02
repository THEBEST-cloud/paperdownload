import httpx

from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "crossref"

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
_ORDER = {"text-mining": 0, "syndication": 1, "unspecified": 2, "": 3, "similarity-checking": 4}


def _is_pdf_link(link: dict) -> bool:
    ct = (link.get("content_type") or "").lower()
    url = (link.get("url") or "").lower()
    return "pdf" in ct or url.endswith(".pdf") or "/pdf" in url


def pdf_candidates(links: list) -> list:
    pdfs = [l for l in links if _is_pdf_link(l)]
    pdfs.sort(key=lambda l: _ORDER.get(l.get("intended_application", ""), 3))
    out, seen = [], set()
    for l in pdfs:
        u = l.get("url", "")
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download(page, md: Metadata) -> DownloadResult:
    candidates = pdf_candidates(md.links)
    if not candidates:
        return DownloadResult(ok=False, reason="no_pdf")
    last_reason = "no_pdf"
    for url in candidates:
        try:
            with httpx.Client(timeout=90, follow_redirects=True, trust_env=False,
                              headers={"User-Agent": _UA, "Accept": "application/pdf"}) as c:
                r = c.get(url)
        except Exception:
            last_reason = "timeout"
            continue
        if r.status_code != 200:
            last_reason = "no_access"
            continue
        body = r.content
        if body[:5].startswith(b"%PDF"):
            return DownloadResult(ok=True, pdf_bytes=body)
        last_reason = "blocked"  # 拿到非 PDF(反爬/HTML)
    return DownloadResult(ok=False, reason=last_reason)
