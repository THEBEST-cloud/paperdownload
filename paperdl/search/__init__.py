from typing import Optional

from paperdl.search.base import Paper, SearchQuery, SearchPage, SearchSource
from paperdl.search.openalex import OpenAlexSource
from paperdl.credentials import load_env

__all__ = ["Paper", "SearchQuery", "SearchPage", "SearchSource",
           "get_source", "resolve_mailto"]


def resolve_mailto(base=None) -> Optional[str]:
    """从 load_env(base) 取 OPENALEX_MAILTO，否则 CSTCLOUD_ID，否则 None。"""
    cfg = load_env(base)
    return cfg.get("OPENALEX_MAILTO") or cfg.get("CSTCLOUD_ID") or None


def get_source(name: str = "openalex", base=None) -> SearchSource:
    """根据名称返回对应的检索源；name=="openalex" → OpenAlexSource；未知名抛 ValueError。"""
    if name == "openalex":
        return OpenAlexSource(mailto=resolve_mailto(base))
    raise ValueError("未知检索源: %s" % name)
