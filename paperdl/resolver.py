from dataclasses import dataclass, field
from typing import Optional

import httpx

CROSSREF_API = "https://api.crossref.org/works/"
# 礼貌池：带邮箱的 UA 让 Crossref 给更稳定的服务
USER_AGENT = "paperdl/0.1 (mailto:FjgracieannnFU@columnist.com)"


@dataclass
class Metadata:
    doi: str
    publisher: str = ""
    title: str = ""
    container: str = ""
    first_author: str = ""
    year: Optional[int] = None
    url: str = ""
    links: list = field(default_factory=list)


def parse_crossref(doi: str, raw: dict) -> Metadata:
    msg = raw.get("message", {})

    title_list = msg.get("title") or []
    container_list = msg.get("container-title") or []

    first_author = ""
    for a in msg.get("author", []) or []:
        if a.get("sequence") == "first" or first_author == "":
            first_author = a.get("family", "") or first_author
            if a.get("sequence") == "first":
                break

    year = None
    parts = (msg.get("issued") or {}).get("date-parts") or []
    if parts and parts[0]:
        year = parts[0][0]

    url = msg.get("URL", "") or ""
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]

    links = []
    for l in msg.get("link", []) or []:
        links.append({
            "url": l.get("URL", "") or "",
            "content_type": l.get("content-type", "") or "",
            "intended_application": l.get("intended-application", "") or "",
        })

    return Metadata(
        doi=doi,
        publisher=msg.get("publisher", "") or "",
        title=(title_list[0] if title_list else "") or "",
        container=(container_list[0] if container_list else "") or "",
        first_author=first_author,
        year=year,
        url=url,
        links=links,
    )


def fetch_metadata(doi: str, client: Optional[httpx.Client] = None) -> Metadata:
    own = client is None
    client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
    try:
        resp = client.get(CROSSREF_API + doi)
        resp.raise_for_status()
        return parse_crossref(doi, resp.json())
    finally:
        if own:
            client.close()
