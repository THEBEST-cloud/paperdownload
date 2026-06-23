# paperdl/search/openalex.py
# OpenAlex /works 检索源：参数拼装、倒排摘要还原、字段映射
from typing import Optional

import httpx

from paperdl.search.base import Paper, SearchQuery, SearchPage

WORKS_URL = "https://api.openalex.org/works"
_UA = "paperdl/1.0 (mailto research tool)"


def reconstruct_abstract(inv: Optional[dict]) -> str:
    """把 OpenAlex 倒排索引还原成文本；None/空 → ''。"""
    if not inv:
        return ""
    positions = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda t: t[0])
    return " ".join(w for _, w in positions)


def _bare_doi(doi: Optional[str]) -> Optional[str]:
    """去掉 https://doi.org/ 前缀，返回裸 DOI；无则 None。"""
    if not doi:
        return None
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "")


def build_params(q: SearchQuery, mailto: Optional[str]) -> dict:
    """把 SearchQuery 拼成 OpenAlex /works 查询参数 dict。"""
    params = {"search": q.query, "per-page": q.per_page, "page": q.page}
    filters = []
    if q.work_type:
        filters.append("type:%s" % q.work_type)
    if q.year_from:
        filters.append("from_publication_date:%d-01-01" % q.year_from)
    if q.year_to:
        filters.append("to_publication_date:%d-12-31" % q.year_to)
    if q.oa_only:
        filters.append("is_oa:true")
    if filters:
        params["filter"] = ",".join(filters)
    # 排序：relevance 不加 sort（OpenAlex 带 search 时默认按相关度）
    if q.sort == "cited":
        params["sort"] = "cited_by_count:desc"
    elif q.sort == "year":
        params["sort"] = "publication_date:desc"
    if mailto:
        params["mailto"] = mailto
    return params


def parse_response(data: dict) -> SearchPage:
    """把 OpenAlex JSON 解析成 SearchPage。"""
    out = []
    for w in data.get("results", []):
        loc = (w.get("primary_location") or {})
        src = (loc.get("source") or {})
        oa = (w.get("open_access") or {})
        out.append(Paper(
            title=w.get("title") or "",
            authors=[(a.get("author") or {}).get("display_name", "")
                     for a in (w.get("authorships") or [])],
            year=w.get("publication_year"),
            venue=src.get("display_name", "") or "",
            doi=_bare_doi(w.get("doi")),
            cited_by=w.get("cited_by_count", 0) or 0,
            is_oa=bool(oa.get("is_oa", False)),
            abstract=reconstruct_abstract(w.get("abstract_inverted_index")),
            type=w.get("type", "") or "",
            oa_url=oa.get("oa_url"),
        ))
    total = (data.get("meta") or {}).get("count", 0) or 0
    return SearchPage(results=out, total=total, page=0, per_page=len(out))


class OpenAlexSource:
    """OpenAlex 检索源，实现 SearchSource 协议。"""

    def __init__(self, mailto: Optional[str] = None, client=None):
        self.mailto = mailto
        self._client = client  # 注入 fake client 供测试使用

    def search(self, q: SearchQuery) -> SearchPage:
        params = build_params(q, self.mailto)
        if self._client is not None:
            resp = self._client.get(WORKS_URL, params=params)
            resp.raise_for_status()
            page = parse_response(resp.json())
        else:
            with httpx.Client(timeout=30, trust_env=False,
                              headers={"User-Agent": _UA}) as c:
                resp = c.get(WORKS_URL, params=params)
                resp.raise_for_status()
                page = parse_response(resp.json())
        page.page = q.page
        page.per_page = q.per_page
        return page
