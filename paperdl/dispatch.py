from typing import Optional

# 阶段 0 只注册 Springer。后续阶段在此表追加。
# 按出版商名称关键词匹配，兜底按 DOI 前缀匹配。
_PUBLISHER_KEYWORDS = {
    "springer": ["springer"],
}
_DOI_PREFIXES = {
    "10.1007": "springer",
}


def adapter_key_for(publisher: str, doi: str) -> Optional[str]:
    pub = (publisher or "").lower()
    for key, words in _PUBLISHER_KEYWORDS.items():
        if any(w in pub for w in words):
            return key
    prefix = doi.split("/")[0] if "/" in doi else ""
    return _DOI_PREFIXES.get(prefix)
