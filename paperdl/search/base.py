from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class Paper:
    title: str = ""
    authors: list = field(default_factory=list)
    year: Optional[int] = None
    venue: str = ""
    doi: Optional[str] = None
    cited_by: int = 0
    is_oa: bool = False
    abstract: str = ""
    type: str = ""
    oa_url: Optional[str] = None


@dataclass
class SearchQuery:
    query: str
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    oa_only: bool = False
    work_type: str = "article"
    sort: str = "relevance"   # relevance | cited | year
    page: int = 1
    per_page: int = 25


@dataclass
class SearchPage:
    results: list = field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 25


class SearchSource(Protocol):
    def search(self, q: SearchQuery) -> SearchPage:
        ...
