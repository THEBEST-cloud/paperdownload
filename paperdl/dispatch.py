from typing import Optional

_DOI_PREFIXES = {
    "10.1007": "springer",
    "10.1016": "elsevier",
    "10.1038": "nature",
    "10.1021": "acs",
    "10.1039": "rsc",
    "10.1002": "wiley",
    "10.1111": "wiley",
    "10.1029": "wiley",
    "10.3389": "frontiers",
    "10.1109": "ieee",
}
_PUBLISHER_KEYWORDS = {
    "springer": ["springer"],
    "elsevier": ["elsevier"],
    "acs": ["american chemical society"],
    "rsc": ["royal society of chemistry"],
    "wiley": ["wiley"],
    "frontiers": ["frontiers media"],
    "ieee": ["ieee"],
}


def adapter_key_for(publisher: str, doi: str) -> Optional[str]:
    prefix = doi.split("/")[0] if "/" in doi else ""
    if prefix in _DOI_PREFIXES:
        return _DOI_PREFIXES[prefix]
    pub = (publisher or "").lower()
    for key, words in _PUBLISHER_KEYWORDS.items():
        if any(w in pub for w in words):
            return key
    return None
