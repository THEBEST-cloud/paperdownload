# OpenAlex 文献检索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 paperdl 加"按关键词检索文献"的前段能力(OpenAlex 数据源),CLI + 网页可浏览/筛选/勾选下载/导出。

**Architecture:** 仿照下载端"多适配器"思路,新建 `paperdl/search/` 可插拔检索源模块:`base.py` 定义数据类与 `SearchSource` 协议,`openalex.py` 实现 OpenAlex,`export.py` 做三种导出。CLI 加 `search` 子命令;网页加检索视图与 `/api/search*` 路由,勾选下载复用现有 `JobManager`。

**Tech Stack:** Python 3、httpx(已有,`trust_env=False` 强制直连)、argparse、FastAPI(已有)、pytest(已有)。

## Global Constraints

- HTTP 请求一律 `httpx.Client(..., trust_env=False)` 强制直连,**不继承系统代理**(项目红线:代理会导致出口 IP 异常)。复制现有 `paperdl/adapters/crossref.py` 的客户端写法。
- OpenAlex 调用必须带 `mailto=` 参数走礼貌池;值取 `load_env()` 的 `OPENALEX_MAILTO`,没有则回退 `CSTCLOUD_ID`(中科院邮箱),再没有则省略该参数。
- 不新增第三方依赖(httpx/fastapi/uvicorn 均已在用)。
- 测试**不打真实网络**:OpenAlex 解析/参数拼装做成纯函数,用录制的 JSON fixture 测;HTTP 调用层用注入的 client 或 monkeypatch。
- 新代码风格、注释密度与中文注释习惯对齐现有 `paperdl/` 文件。

---

### Task 1: 检索数据类型与协议(base.py)

**Files:**
- Create: `paperdl/search/__init__.py`(本任务先建空文件,Task 3 再填注册表)
- Create: `paperdl/search/base.py`
- Test: `tests/test_search_base.py`

**Interfaces:**
- Consumes: 无。
- Produces:
  - `@dataclass Paper`:字段 `title:str, authors:list[str], year:Optional[int], venue:str, doi:Optional[str], cited_by:int, is_oa:bool, abstract:str, type:str, oa_url:Optional[str]`,全部有默认值(`title=""`、`authors=field(default_factory=list)`、`year=None`、`cited_by=0`、`is_oa=False` 等)。
  - `@dataclass SearchQuery`:`query:str, year_from:Optional[int]=None, year_to:Optional[int]=None, oa_only:bool=False, work_type:str="article", sort:str="relevance", page:int=1, per_page:int=25`。
  - `@dataclass SearchPage`:`results:list[Paper]=field(default_factory=list), total:int=0, page:int=1, per_page:int=25`。
  - `class SearchSource(Protocol)`:方法 `search(self, q: SearchQuery) -> SearchPage`。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_base.py
from paperdl.search.base import Paper, SearchQuery, SearchPage


def test_paper_defaults():
    p = Paper(title="Hello")
    assert p.authors == []
    assert p.year is None
    assert p.cited_by == 0
    assert p.is_oa is False
    assert p.doi is None


def test_searchquery_defaults():
    q = SearchQuery(query="microplastics")
    assert q.sort == "relevance"
    assert q.work_type == "article"
    assert q.page == 1
    assert q.per_page == 25


def test_searchpage_defaults():
    sp = SearchPage()
    assert sp.results == []
    assert sp.total == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_base.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'paperdl.search'`

- [ ] **Step 3: Write minimal implementation**

```python
# paperdl/search/__init__.py
# (本任务留空;Task 3 填注册表)
```

```python
# paperdl/search/base.py
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
```

说明:`tests/` 是扁平布局(已是包,有 `tests/__init__.py`),测试文件直接放 `tests/test_search_*.py`,fixtures 放已存在的 `tests/fixtures/`。无需新建子目录。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_base.py -q`
Expected: PASS(3 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdl/search/__init__.py paperdl/search/base.py tests/test_search_base.py
git commit -m "feat(search): 检索数据类型与 SearchSource 协议"
```

---

### Task 2: OpenAlex 检索源(openalex.py)

**Files:**
- Create: `paperdl/search/openalex.py`
- Test: `tests/test_search_openalex.py`
- Test fixture: `tests/fixtures/openalex_works.json`(从真实响应裁剪 2 条结果,含一条有 `abstract_inverted_index`、一条 `abstract_inverted_index=null`)

**Interfaces:**
- Consumes: `paperdl.search.base.{Paper, SearchQuery, SearchPage}`。
- Produces:
  - `def reconstruct_abstract(inv: Optional[dict]) -> str`:把 OpenAlex 倒排索引还原成文本;`None`/空 → `""`。
  - `def build_params(q: SearchQuery, mailto: Optional[str]) -> dict`:把 `SearchQuery` 拼成 OpenAlex `/works` 查询参数 dict。
  - `def parse_response(data: dict) -> SearchPage`:把 OpenAlex JSON 解析成 `SearchPage`。
  - `class OpenAlexSource`:`__init__(self, mailto: Optional[str]=None, client=None)`;`search(self, q: SearchQuery) -> SearchPage`。

**OpenAlex 字段映射(parse_response 内)**:每个 `results[i]` → `Paper(title=w["title"] or "", authors=[a["author"]["display_name"] for a in w.get("authorships",[])], year=w.get("publication_year"), venue=(w.get("primary_location") or {}).get("source",{}) or {}).get("display_name","")` —— 注意防御 None;`doi`=去掉 `https://doi.org/` 前缀后的裸 DOI(`w.get("doi")` 形如 `https://doi.org/10.x`,无则 None);`cited_by=w.get("cited_by_count",0)`;`is_oa=(w.get("open_access") or {}).get("is_oa", False)`;`oa_url=(w.get("open_access") or {}).get("oa_url")`;`abstract=reconstruct_abstract(w.get("abstract_inverted_index"))`;`type=w.get("type","")`。`total=(data.get("meta") or {}).get("count",0)`。

**build_params 规则**:
- `search=q.query`。
- `per-page=q.per_page`,`page=q.page`。
- filter 用逗号拼接的列表组装成一个字符串:
  - 始终(除非 work_type 为空)加 `type:{q.work_type}`。
  - `q.year_from` → `from_publication_date:{year_from}-01-01`。
  - `q.year_to` → `to_publication_date:{year_to}-12-31`。
  - `q.oa_only` → `is_oa:true`。
  - 拼好后作为 `filter` 键(无任何条件则不加 `filter`)。
- 排序:`relevance` 不加 `sort`(OpenAlex 带 search 时默认按相关度);`cited` → `sort=cited_by_count:desc`;`year` → `sort=publication_date:desc`。
- `mailto` 非空 → 加 `mailto`。

- [ ] **Step 1: Write the failing test**

先放一份裁剪后的 fixture(2 条结果),再写测试:

```python
# tests/test_search_openalex.py
import json
from pathlib import Path

from paperdl.search.base import SearchQuery
from paperdl.search.openalex import (
    reconstruct_abstract, build_params, parse_response, OpenAlexSource,
)

FIX = Path(__file__).parent / "fixtures" / "openalex_works.json"


def test_reconstruct_abstract():
    inv = {"Hello": [0], "world": [1], "again": [2]}
    assert reconstruct_abstract(inv) == "Hello world again"


def test_reconstruct_abstract_empty():
    assert reconstruct_abstract(None) == ""
    assert reconstruct_abstract({}) == ""


def test_build_params_basic():
    p = build_params(SearchQuery(query="microplastics"), mailto="a@b.cn")
    assert p["search"] == "microplastics"
    assert p["filter"] == "type:article"
    assert p["mailto"] == "a@b.cn"
    assert "sort" not in p


def test_build_params_filters_and_sort():
    q = SearchQuery(query="x", year_from=2020, year_to=2025, oa_only=True, sort="cited")
    p = build_params(q, mailto=None)
    assert "from_publication_date:2020-01-01" in p["filter"]
    assert "to_publication_date:2025-12-31" in p["filter"]
    assert "is_oa:true" in p["filter"]
    assert p["sort"] == "cited_by_count:desc"
    assert "mailto" not in p


def test_parse_response_maps_fields():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    page = parse_response(data)
    assert page.total > 0
    first = page.results[0]
    assert first.title
    assert first.doi and not first.doi.startswith("http")
    assert isinstance(first.authors, list)
    # fixture 第二条 abstract_inverted_index 为 null
    assert page.results[1].abstract == ""


def test_search_uses_injected_client(monkeypatch):
    data = json.loads(FIX.read_text(encoding="utf-8"))

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return data

    class FakeClient:
        def __init__(self): self.last = None
        def get(self, url, params=None):
            self.last = (url, params)
            return FakeResp()

    fake = FakeClient()
    src = OpenAlexSource(mailto="a@b.cn", client=fake)
    page = src.search(SearchQuery(query="x"))
    assert page.total > 0
    assert "openalex.org/works" in fake.last[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_openalex.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'paperdl.search.openalex'`(或 fixture 缺失错误)

- [ ] **Step 3: Write minimal implementation**

先建 fixture `tests/fixtures/openalex_works.json`(裁剪真实 `/works` 响应,保留 `meta.count`、两条 `results`,每条含 `title/doi/publication_year/authorships/cited_by_count/open_access/type/primary_location`,第一条带 `abstract_inverted_index`,第二条 `abstract_inverted_index: null`)。

```python
# paperdl/search/openalex.py
from typing import Optional

import httpx

from paperdl.search.base import Paper, SearchQuery, SearchPage

WORKS_URL = "https://api.openalex.org/works"
_UA = "paperdl/1.0 (mailto research tool)"


def reconstruct_abstract(inv: Optional[dict]) -> str:
    if not inv:
        return ""
    positions = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda t: t[0])
    return " ".join(w for _, w in positions)


def _bare_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "")


def build_params(q: SearchQuery, mailto: Optional[str]) -> dict:
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
    if q.sort == "cited":
        params["sort"] = "cited_by_count:desc"
    elif q.sort == "year":
        params["sort"] = "publication_date:desc"
    if mailto:
        params["mailto"] = mailto
    return params


def parse_response(data: dict) -> SearchPage:
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
    def __init__(self, mailto: Optional[str] = None, client=None):
        self.mailto = mailto
        self._client = client

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_openalex.py -q`
Expected: PASS(全部 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdl/search/openalex.py tests/test_search_openalex.py tests/fixtures/openalex_works.json
git commit -m "feat(search): OpenAlex 检索源(参数拼装/倒排摘要还原/字段映射)"
```

---

### Task 3: 检索源注册表(__init__.py)

**Files:**
- Modify: `paperdl/search/__init__.py`
- Test: `tests/test_search_registry.py`

**Interfaces:**
- Consumes: `paperdl.search.openalex.OpenAlexSource`;`paperdl.credentials.load_env`。
- Produces:
  - `def resolve_mailto(base=None) -> Optional[str]`:从 `load_env(base)` 取 `OPENALEX_MAILTO`,否则 `CSTCLOUD_ID`,否则 None。
  - `def get_source(name: str = "openalex", base=None) -> SearchSource`:`name=="openalex"` → `OpenAlexSource(mailto=resolve_mailto(base))`;未知名抛 `ValueError`。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_registry.py
import pytest
from paperdl.search import get_source
from paperdl.search.openalex import OpenAlexSource


def test_get_source_default():
    s = get_source()
    assert isinstance(s, OpenAlexSource)


def test_get_source_unknown():
    with pytest.raises(ValueError):
        get_source("nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_registry.py -q`
Expected: FAIL — `ImportError: cannot import name 'get_source'`

- [ ] **Step 3: Write minimal implementation**

```python
# paperdl/search/__init__.py
from typing import Optional

from paperdl.search.base import Paper, SearchQuery, SearchPage, SearchSource
from paperdl.search.openalex import OpenAlexSource
from paperdl.credentials import load_env

__all__ = ["Paper", "SearchQuery", "SearchPage", "SearchSource",
           "get_source", "resolve_mailto"]


def resolve_mailto(base=None) -> Optional[str]:
    cfg = load_env(base)
    return cfg.get("OPENALEX_MAILTO") or cfg.get("CSTCLOUD_ID") or None


def get_source(name: str = "openalex", base=None) -> SearchSource:
    if name == "openalex":
        return OpenAlexSource(mailto=resolve_mailto(base))
    raise ValueError("未知检索源: %s" % name)
```

确认 `load_env` 接受 `base` 参数(credentials.py:22 `def load_env(base=None)`),签名匹配。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_registry.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperdl/search/__init__.py tests/test_search_registry.py
git commit -m "feat(search): 检索源注册表 get_source + mailto 解析"
```

---

### Task 4: 导出器(export.py — DOI 清单 / CSV / BibTeX)

**Files:**
- Create: `paperdl/search/export.py`
- Test: `tests/test_search_export.py`

**Interfaces:**
- Consumes: `paperdl.search.base.Paper`。
- Produces:
  - `def to_doi_list(papers: list) -> str`:每行一个裸 DOI,跳过无 DOI 的;末尾换行。
  - `def to_csv(papers: list) -> str`:表头 `title,authors,year,venue,doi,cited_by,is_oa,type`;authors 用 `; ` 连接;用 `csv` 模块正确转义。
  - `def to_bibtex(papers: list) -> str`:每篇一个 `@article`,key=`第一作者姓_年_首词`(无作者用 `anon`,无年用 `n.d.`),字段 title/author/journal/year/doi;多篇用空行分隔。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_export.py
from paperdl.search.base import Paper
from paperdl.search.export import to_doi_list, to_csv, to_bibtex

P1 = Paper(title="Microplastics in water", authors=["Jane Doe", "Li Wei"],
           year=2021, venue="Water Research", doi="10.1016/j.watres.2021.117056",
           cited_by=42, is_oa=True, type="article")
P2 = Paper(title="No DOI here", authors=[], year=2019, venue="Unknown", doi=None)


def test_to_doi_list_skips_missing():
    out = to_doi_list([P1, P2])
    assert out.strip() == "10.1016/j.watres.2021.117056"


def test_to_csv_has_header_and_row():
    out = to_csv([P1])
    lines = out.strip().splitlines()
    assert lines[0] == "title,authors,year,venue,doi,cited_by,is_oa,type"
    assert "Microplastics in water" in lines[1]
    assert "Jane Doe; Li Wei" in lines[1]


def test_to_bibtex():
    out = to_bibtex([P1])
    assert "@article{" in out
    assert "title = {Microplastics in water}" in out
    assert "doi = {10.1016/j.watres.2021.117056}" in out
    assert "year = {2021}" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_export.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'paperdl.search.export'`

- [ ] **Step 3: Write minimal implementation**

```python
# paperdl/search/export.py
import csv
import io
import re


def to_doi_list(papers: list) -> str:
    lines = [p.doi for p in papers if p.doi]
    return "\n".join(lines) + ("\n" if lines else "")


def to_csv(papers: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["title", "authors", "year", "venue", "doi", "cited_by", "is_oa", "type"])
    for p in papers:
        w.writerow([p.title, "; ".join(p.authors), p.year or "", p.venue,
                    p.doi or "", p.cited_by, p.is_oa, p.type])
    return buf.getvalue()


def _cite_key(p) -> str:
    surname = "anon"
    if p.authors:
        surname = re.sub(r"\W+", "", p.authors[0].split()[-1]) or "anon"
    year = str(p.year) if p.year else "nd"
    first = re.sub(r"\W+", "", (p.title.split()[0] if p.title else "")) or "x"
    return "%s_%s_%s" % (surname, year, first)


def to_bibtex(papers: list) -> str:
    blocks = []
    for p in papers:
        fields = []
        if p.title:
            fields.append("  title = {%s}" % p.title)
        if p.authors:
            fields.append("  author = {%s}" % " and ".join(p.authors))
        if p.venue:
            fields.append("  journal = {%s}" % p.venue)
        if p.year:
            fields.append("  year = {%d}" % p.year)
        if p.doi:
            fields.append("  doi = {%s}" % p.doi)
        blocks.append("@article{%s,\n%s\n}" % (_cite_key(p), ",\n".join(fields)))
    return "\n\n".join(blocks) + ("\n" if blocks else "")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_export.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperdl/search/export.py tests/test_search_export.py
git commit -m "feat(search): 导出器(DOI 清单 / CSV / BibTeX)"
```

---

### Task 5: CLI `paperdl search` 命令

**Files:**
- Modify: `paperdl/cli.py`(在 `build_parser` 加 subparser;`main` 加分发;新增 `_do_search`)
- Test: `tests/test_search_cli.py`

**Interfaces:**
- Consumes: `paperdl.search.{get_source}`、`paperdl.search.base.SearchQuery`、`paperdl.search.export.{to_doi_list,to_csv,to_bibtex}`。
- Produces: CLI 行为(可经 `paperdl.cli.main(argv)` 调用)。`_do_search(args)` 用 `get_source().search(SearchQuery(...))`,无导出参数则打印表格,有 `-o/--csv/--bib` 则写文件。

**子命令参数**(在 `build_parser` 内):
```python
ps = sub.add_parser("search", help="按关键词检索文献(OpenAlex)")
ps.add_argument("query", help="检索关键词")
ps.add_argument("--from", dest="year_from", type=int, default=None, help="起始年份")
ps.add_argument("--to", dest="year_to", type=int, default=None, help="结束年份")
ps.add_argument("--oa", action="store_true", help="仅开放获取")
ps.add_argument("--sort", choices=["relevance", "cited", "year"], default="relevance")
ps.add_argument("--type", dest="work_type", default="article", help="文献类型(默认 article)")
ps.add_argument("-n", "--num", type=int, default=25, help="结果数量(<=200)")
ps.add_argument("-o", "--out", default=None, help="导出 DOI 清单到文件")
ps.add_argument("--csv", default=None, help="导出 CSV 到文件")
ps.add_argument("--bib", default=None, help="导出 BibTeX 到文件")
```
`main` 分发:`elif args.command == "search": _do_search(args)`。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_cli.py
from pathlib import Path

import paperdl.cli as cli
from paperdl.search.base import Paper, SearchPage


def _fake_source(papers):
    class S:
        def search(self, q):
            return SearchPage(results=papers, total=len(papers), page=1, per_page=25)
    return S()


def test_search_prints_table(monkeypatch, capsys):
    papers = [Paper(title="Hello world", authors=["A B"], year=2021,
                    doi="10.1/x", cited_by=5, is_oa=True)]
    monkeypatch.setattr(cli, "get_source", lambda *a, **k: _fake_source(papers))
    cli.main(["search", "hello"])
    out = capsys.readouterr().out
    assert "Hello world" in out
    assert "10.1/x" in out


def test_search_exports_doi_list(monkeypatch, tmp_path):
    papers = [Paper(title="X", doi="10.1/x"), Paper(title="Y", doi="10.2/y")]
    monkeypatch.setattr(cli, "get_source", lambda *a, **k: _fake_source(papers))
    out = tmp_path / "list.txt"
    cli.main(["search", "x", "-o", str(out)])
    assert out.read_text().split() == ["10.1/x", "10.2/y"]
```

注意:测试 monkeypatch 的是 `cli.get_source`,故 `cli.py` 必须 `from paperdl.search import get_source`(模块级名字),`_do_search` 内直接用 `get_source(...)`。

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_cli.py -q`
Expected: FAIL — `argument command: invalid choice: 'search'`(或 `get_source` 未定义)

- [ ] **Step 3: Write minimal implementation**

在 `paperdl/cli.py` 顶部加导入:
```python
from paperdl.search import get_source
from paperdl.search.base import SearchQuery
from paperdl.search.export import to_doi_list, to_csv, to_bibtex
```
在 `build_parser` 的 `serve` 之后加上面的 `search` subparser 块。
新增函数:
```python
def _do_search(args) -> None:
    src = get_source()
    page = src.search(SearchQuery(
        query=args.query, year_from=args.year_from, year_to=args.year_to,
        oa_only=args.oa, work_type=args.work_type, sort=args.sort,
        per_page=min(args.num, 200), page=1,
    ))
    papers = page.results
    wrote = False
    if args.out:
        Path(args.out).write_text(to_doi_list(papers), encoding="utf-8")
        print("已写 DOI 清单 → %s (%d 条)" % (args.out, sum(1 for p in papers if p.doi)))
        wrote = True
    if args.csv:
        Path(args.csv).write_text(to_csv(papers), encoding="utf-8")
        print("已写 CSV → %s" % args.csv)
        wrote = True
    if args.bib:
        Path(args.bib).write_text(to_bibtex(papers), encoding="utf-8")
        print("已写 BibTeX → %s" % args.bib)
        wrote = True
    if wrote:
        return
    print("共约 %d 条,显示前 %d:" % (page.total, len(papers)))
    for i, p in enumerate(papers, 1):
        au = (p.authors[0] + " 等") if p.authors else "—"
        oa = "OA" if p.is_oa else "  "
        print("%2d. [%s] %s (%s, %s) 被引%d  %s"
              % (i, oa, p.title[:70], au, p.year or "—", p.cited_by, p.doi or "无DOI"))
```
在 `main` 加分发:`elif args.command == "search": _do_search(args)`。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_cli.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperdl/cli.py tests/test_search_cli.py
git commit -m "feat(search): CLI paperdl search 命令(打印/导出)"
```

---

### Task 6: 网页 API 路由(检索 / 导出 / 勾选下载)

**Files:**
- Modify: `paperdl/web/app.py`(加 3 个路由)
- Test: `tests/test_search_web.py`

**Interfaces:**
- Consumes: `paperdl.search.{get_source}`、`SearchQuery`、`export.*`;现有 `mgr`(JobManager)、`current_user`、`_new_id`。
- Produces:
  - `GET /api/search`:query 参数 `q, year_from, year_to, oa, sort, type, page, per_page`;返回 `{results:[...], total, page, per_page}`(Paper 用 `dataclasses.asdict`)。需登录。
  - `POST /api/search/export`:body `{dois?:[...], papers?:[...], format:"doi|csv|bib"}` — 简化为接收前端已选 `papers`(Paper 字段 dict 列表)+ `format`,返回对应文本文件(`Response` + `Content-Disposition`)。需登录。
  - `POST /api/search/download`:body `{dois:[...]}`,复用 `mgr.create(_new_id(), ..., dois, owner=user)` + `mgr.start(job)`,返回 `{job_id}`。需登录。(等价于现有 `/api/jobs`,语义上是"把检索勾选送去下载";直接复用现有 `/api/jobs` 亦可 — 但显式路由让前端意图清晰。)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search_web.py
import paperdl.web.app as webapp
from paperdl.search.base import Paper, SearchPage
from fastapi.testclient import TestClient


def _login_client(monkeypatch):
    # 绕过鉴权:直接覆盖依赖
    webapp.app.dependency_overrides[webapp.current_user] = lambda: "tester"
    return TestClient(webapp.app)


def test_search_route(monkeypatch):
    papers = [Paper(title="Hello", doi="10.1/x", year=2021, cited_by=3)]
    monkeypatch.setattr(webapp, "get_source",
                        lambda *a, **k: type("S", (), {"search": lambda self, q: SearchPage(results=papers, total=1)})())
    c = _login_client(monkeypatch)
    try:
        r = c.get("/api/search", params={"q": "hello"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["results"][0]["doi"] == "10.1/x"
    finally:
        webapp.app.dependency_overrides.clear()


def test_export_route(monkeypatch):
    c = _login_client(monkeypatch)
    try:
        r = c.post("/api/search/export",
                   json={"papers": [{"title": "X", "doi": "10.1/x", "authors": [], "year": 2020}],
                         "format": "doi"})
        assert r.status_code == 200
        assert "10.1/x" in r.text
    finally:
        webapp.app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_web.py -q`
Expected: FAIL — 404(路由不存在)

- [ ] **Step 3: Write minimal implementation**

在 `paperdl/web/app.py` 顶部加导入:
```python
from dataclasses import asdict
from paperdl.search import get_source
from paperdl.search.base import SearchQuery
from paperdl.search.base import Paper
from paperdl.search.export import to_doi_list, to_csv, to_bibtex
```
加路由:
```python
@app.get("/api/search")
def api_search(q: str, year_from: int = None, year_to: int = None,
               oa: bool = False, sort: str = "relevance", type: str = "article",
               page: int = 1, per_page: int = 25, user: str = Depends(current_user)):
    src = get_source()
    sp = src.search(SearchQuery(query=q, year_from=year_from, year_to=year_to,
                                oa_only=oa, work_type=type, sort=sort,
                                page=page, per_page=min(per_page, 200)))
    return {"results": [asdict(p) for p in sp.results],
            "total": sp.total, "page": sp.page, "per_page": sp.per_page}


@app.post("/api/search/export")
def api_search_export(payload: dict, user: str = Depends(current_user)):
    rows = payload.get("papers") or []
    papers = [Paper(**{k: r.get(k) for k in
                       ("title", "authors", "year", "venue", "doi",
                        "cited_by", "is_oa", "abstract", "type", "oa_url")
                       if r.get(k) is not None}) for r in rows]
    fmt = payload.get("format", "doi")
    if fmt == "csv":
        body, media, name = to_csv(papers), "text/csv", "papers.csv"
    elif fmt == "bib":
        body, media, name = to_bibtex(papers), "text/plain", "papers.bib"
    else:
        body, media, name = to_doi_list(papers), "text/plain", "dois.txt"
    return Response(content=body, media_type=media,
                    headers={"Content-Disposition": 'attachment; filename="%s"' % name})


@app.post("/api/search/download")
def api_search_download(payload: dict, user: str = Depends(current_user)):
    dois = [d for d in (payload.get("dois") or []) if d]
    if not dois:
        raise HTTPException(400, "no dois")
    job = mgr.create(_new_id(), datetime.now(timezone.utc).isoformat(), dois, owner=user)
    mgr.start(job)
    return {"job_id": job.id}
```
注意 `Paper(**...)` 只传非 None 字段,避免覆盖 `authors` 默认工厂(authors 为 None 时不传)。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_web.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperdl/web/app.py tests/test_search_web.py
git commit -m "feat(search): 网页 API(检索/导出/勾选下载)"
```

---

### Task 7: 网页检索视图(index.html)

**Files:**
- Modify: `paperdl/web/static/index.html`(加"检索"标签视图 + JS)

**Interfaces:**
- Consumes: `GET /api/search`、`POST /api/search/export`、`POST /api/search/download`。
- Produces: 用户可见的检索界面。此任务为前端 UI,**测试方式为手动验证**(无单测)。

实现要点(对齐现有单页结构与样式):
- 顶部导航加「检索」入口,与现有「下载」视图切换(沿用现有 view 切换写法)。
- 检索视图含:搜索输入框 + 「搜索」按钮;筛选行(起始年/结束年 number 输入、仅 OA 复选、排序下拉 relevance/cited/year);结果容器;分页「上一页/下一页」(用 page 状态);底部操作条「下载选中」「导出 DOI/CSV/BibTeX」。
- JS:
  - `doSearch(page)` → `fetch('/api/search?'+new URLSearchParams({q,year_from,year_to,oa,sort,page}))` → 渲染结果卡片(标题、作者前 3、年、来源、被引、OA 徽章、摘要可展开),每条一个 checkbox(value=DOI,data 存整条 paper JSON)。
  - 「下载选中」→ 收集勾选 DOI → `POST /api/search/download {dois}` → 提示 job 已建,跳到下载视图看进度。
  - 「导出」→ 收集勾选的 paper 对象 → `POST /api/search/export {papers, format}` → 用 blob 触发下载。
  - 无勾选时操作按钮提示"请先勾选"。
- 失败处理:fetch 非 200 时弹出错误文本(沿用现有错误提示方式)。

- [ ] **Step 1: 加检索视图骨架与导航切换**

在现有视图容器旁加 `<section id="view-search">`,导航加按钮调用现有切换函数。提交前用浏览器开 `paperdl serve` 确认能切到空白检索页。

- [ ] **Step 2: 实现 doSearch 渲染结果**

加搜索框/筛选/结果渲染 JS(见上要点)。

- [ ] **Step 3: 实现勾选下载与导出**

加「下载选中」「导出」逻辑。

- [ ] **Step 4: 手动验证**

```bash
python -m paperdl serve --port 8200
```
浏览器(或 SSH 端口转发)打开 → 注册/登录 → 检索 "microplastics" → 看到结果 → 勾选两条 → 「下载选中」→ 切到下载视图看到新任务 → 回检索「导出 BibTeX」下载到 .bib。

- [ ] **Step 5: Commit**

```bash
git add paperdl/web/static/index.html
git commit -m "feat(search): 网页检索视图(搜索/筛选/勾选下载/导出)"
```

---

### Task 8: 文档与配置收尾(README / env 模板 / 回归)

**Files:**
- Modify: `README.md`
- Modify: `.paperdl.env.example`(加 `OPENALEX_MAILTO=`)
- 验证: `scripts/make_skill.py` 无需改(`rglob` 整包拷 `paperdl/`,`paperdl/search/` 自动包含)

**Interfaces:**
- Consumes: 全部已实现功能。
- Produces: 用户文档。

- [ ] **Step 1: 加 env 模板项**

在 `.paperdl.env.example` 末尾加:
```
# 可选：OpenAlex 礼貌池邮箱(检索功能用;留空则回退用 CSTCLOUD_ID)
OPENALEX_MAILTO=
```

- [ ] **Step 2: 更新 README**

- 顶部能力清单加一条:"**按关键词检索文献**(OpenAlex,可筛选/导出/勾选直接下载)"。
- 新增「## 检索文献(OpenAlex)」小节,放在「快速上手(命令行)」与「网页版」之间,含:
  - CLI 示例:
    ```bash
    paperdl search "microplastics drinking water" --from 2020 --oa --sort cited -n 25
    paperdl search "..." -o list.txt   # 导出 DOI 清单,直接 paperdl run list.txt
    paperdl search "..." --csv out.csv --bib out.bib
    ```
  - 网页:在「检索」页输入关键词 → 侧边按年份/OA/排序筛选 → 勾选论文「下载选中」直接进下载队列,或「导出」DOI/CSV/BibTeX。
  - 一句话:数据源 OpenAlex(免费、无需 key、全学科),DOI 可无缝接 `paperdl run`;WoS 等以后可作为可插拔源加入。
- 「开发」节的代码结构补一句:`paperdl/search/`(检索:base / openalex / export)。

- [ ] **Step 3: 全量回归测试**

Run: `python -m pytest -q`
Expected: 全绿(新增 search 测试 + 原有用例都通过)

- [ ] **Step 4: Commit**

```bash
git add README.md .paperdl.env.example
git commit -m "docs: README + env 模板补充 OpenAlex 检索用法"
```

---

## Self-Review

**Spec 覆盖检查**(逐条对 spec):
- 可插拔架构(base/openalex/__init__ 注册表)→ Task 1/2/3 ✅
- OpenAlex 接入(mailto/倒排摘要/参数映射/排序/限速)→ Task 2/3 ✅(限速:OpenAlex 宽松,本版靠单次请求 + 超时;批量翻页由用户分页驱动,不做并发,符合红线)
- CLI `paperdl search` + 三种导出 → Task 4/5 ✅
- 网页检索页 + 筛选 + 勾选下载 + 导出 → Task 6/7 ✅
- 导出 DOI/CSV/BibTeX → Task 4 ✅
- 测试(fixture 不打真网 / 导出 / web 路由)→ Task 1/2/4/6 ✅
- 实现后更新 README + env + make_skill → Task 8 ✅

**占位符扫描**:无 TBD/TODO;每个代码步骤含完整代码。

**类型一致性**:`Paper/SearchQuery/SearchPage/SearchSource` 字段与方法名在 Task 1 定义,Task 2/4/5/6 引用一致;`get_source`/`SearchQuery` 在 cli 与 web 中名字一致;`to_doi_list/to_csv/to_bibtex` 跨任务一致。

**已知小风险**(实现时留意,非阻塞):
- fixture 需用真实 OpenAlex 响应裁剪(Task 2 实现时可临时 `curl 'https://api.openalex.org/works?search=microplastics&per-page=2'` 取样再裁剪,提交进 repo;之后测试不联网)。
- 测试文件扁平放 `tests/test_search_*.py`,fixture 放 `tests/fixtures/`(已是包,无需新建子目录)。
