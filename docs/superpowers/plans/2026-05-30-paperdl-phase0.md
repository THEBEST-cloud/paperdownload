# paperdl 阶段 0 实现计划（框架 + Springer 跑通）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭好 paperdl 的通用框架，并把 Springer 一家从「DOI 清单 → 登录会话 → 下到 PDF」端到端跑通，验证 CAS 联邦登录会话可脚本化下载。

**Architecture:** Python 命令行工具。纯逻辑（Crossref 解析、文件名、出版商路由、结果记录、限速/重试主循环、PDF 链接提取）走 TDD 单元测试；Playwright 浏览器登录与导航下载部分结构化后用真实登录手动验证。每个适配器拆成「`find_pdf_url(html, base_url)` 纯函数」+「导航下载」两层。

**Tech Stack:** Python 3.11+、Playwright(chromium)、httpx(Crossref)、argparse(CLI)、pytest。

---

### Task 1: 项目脚手架与依赖

**Files:**
- Create: `requirements.txt`
- Create: `paperdl/__init__.py`
- Create: `paperdl/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: 写依赖文件**

`requirements.txt`:
```
playwright>=1.44
httpx>=0.27
pytest>=8.0
```

- [ ] **Step 2: 写包入口**

`paperdl/__init__.py`:
```python
__version__ = "0.1.0"
```

`paperdl/__main__.py`:
```python
from paperdl.cli import main

if __name__ == "__main__":
    main()
```

注意：`paperdl.cli` 在 Task 10 创建。本任务先不导入运行，仅占位，smoke 测试不触达它。

- [ ] **Step 3: 写冒烟测试**

`tests/__init__.py`: 空文件。

`tests/test_smoke.py`:
```python
import paperdl


def test_version():
    assert paperdl.__version__ == "0.1.0"
```

- [ ] **Step 4: 安装依赖并运行测试**

Run:
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python -m playwright install chromium
pytest tests/test_smoke.py -v
```
Expected: PASS（1 passed）。playwright 浏览器安装成功。

- [ ] **Step 5: 提交**

```bash
git add requirements.txt paperdl/ tests/
git commit -m "chore: project scaffold and dependencies"
```

---

### Task 2: resolver.py — Crossref 元数据解析

**Files:**
- Create: `paperdl/resolver.py`
- Create: `tests/fixtures/crossref_springer.json`
- Create: `tests/test_resolver.py`

- [ ] **Step 1: 写测试夹具**

`tests/fixtures/crossref_springer.json`（Crossref `/works/{doi}` 响应的精简真实结构）:
```json
{
  "status": "ok",
  "message": {
    "DOI": "10.1007/s00339-021-04567-w",
    "publisher": "Springer Science and Business Media LLC",
    "title": ["A study of something interesting"],
    "container-title": ["Applied Physics A"],
    "author": [
      {"given": "Wei", "family": "Zhang", "sequence": "first"},
      {"given": "Li", "family": "Chen", "sequence": "additional"}
    ],
    "issued": {"date-parts": [[2021, 6, 15]]},
    "URL": "http://dx.doi.org/10.1007/s00339-021-04567-w"
  }
}
```

- [ ] **Step 2: 写失败测试**

`tests/test_resolver.py`:
```python
import json
from pathlib import Path

from paperdl.resolver import parse_crossref, Metadata

FIX = Path(__file__).parent / "fixtures"


def test_parse_crossref_extracts_fields():
    raw = json.loads((FIX / "crossref_springer.json").read_text())
    md = parse_crossref("10.1007/s00339-021-04567-w", raw)
    assert isinstance(md, Metadata)
    assert md.doi == "10.1007/s00339-021-04567-w"
    assert md.publisher == "Springer Science and Business Media LLC"
    assert md.title == "A study of something interesting"
    assert md.container == "Applied Physics A"
    assert md.first_author == "Zhang"
    assert md.year == 2021
    assert md.url == "https://dx.doi.org/10.1007/s00339-021-04567-w"


def test_parse_crossref_missing_optional_fields():
    md = parse_crossref("10.1/x", {"message": {"DOI": "10.1/x"}})
    assert md.doi == "10.1/x"
    assert md.publisher == ""
    assert md.title == ""
    assert md.first_author == ""
    assert md.year is None
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_resolver.py -v`
Expected: FAIL（ModuleNotFoundError / cannot import name）。

- [ ] **Step 4: 写实现**

`paperdl/resolver.py`:
```python
from dataclasses import dataclass
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

    return Metadata(
        doi=doi,
        publisher=msg.get("publisher", "") or "",
        title=(title_list[0] if title_list else "") or "",
        container=(container_list[0] if container_list else "") or "",
        first_author=first_author,
        year=year,
        url=url,
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
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_resolver.py -v`
Expected: PASS（2 passed）。

- [ ] **Step 6: 提交**

```bash
git add paperdl/resolver.py tests/test_resolver.py tests/fixtures/crossref_springer.json
git commit -m "feat: Crossref metadata resolver"
```

---

### Task 3: naming.py — 文件名构造与清洗

**Files:**
- Create: `paperdl/naming.py`
- Create: `tests/test_naming.py`

- [ ] **Step 1: 写失败测试**

`tests/test_naming.py`:
```python
from paperdl.naming import build_filename
from paperdl.resolver import Metadata


def test_build_filename_normal():
    md = Metadata(doi="10.1007/abc", first_author="Zhang", year=2021,
                  title="A Study of Something Interesting")
    assert build_filename(md) == "Zhang-2021-A Study of Something Interesting.pdf"


def test_build_filename_strips_illegal_chars():
    md = Metadata(doi="10.1/x", first_author="O'Neil", year=2020,
                  title="Title: with / illegal \\ chars?")
    name = build_filename(md)
    for ch in '/\\:?*"<>|':
        assert ch not in name
    assert name.endswith(".pdf")


def test_build_filename_truncates_long_title():
    md = Metadata(doi="10.1/x", first_author="Li", year=2019, title="x" * 200)
    name = build_filename(md)
    assert len(name) <= 100  # 留余量


def test_build_filename_falls_back_to_doi_when_empty():
    md = Metadata(doi="10.1007/abc.def")
    name = build_filename(md)
    assert name == "10.1007_abc.def.pdf"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_naming.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3: 写实现**

`paperdl/naming.py`:
```python
import re

from paperdl.resolver import Metadata

ILLEGAL = r'[\/\\:\?\*"<>\|]'
TITLE_MAX = 80


def _clean(text: str) -> str:
    text = re.sub(ILLEGAL, "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_filename(md: Metadata) -> str:
    author = _clean(md.first_author)
    title = _clean(md.title)
    if author and md.year and title:
        title = title[:TITLE_MAX].strip()
        return f"{author}-{md.year}-{title}.pdf"
    # 缺字段时退回 DOI（DOI 里的 / 换成 _）
    safe_doi = re.sub(ILLEGAL, "_", md.doi)
    return f"{safe_doi}.pdf"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_naming.py -v`
Expected: PASS（4 passed）。

- [ ] **Step 5: 提交**

```bash
git add paperdl/naming.py tests/test_naming.py
git commit -m "feat: filename builder and sanitizer"
```

---

### Task 4: dispatch.py — 出版商 → 适配器路由

**Files:**
- Create: `paperdl/dispatch.py`
- Create: `tests/test_dispatch.py`

- [ ] **Step 1: 写失败测试**

`tests/test_dispatch.py`:
```python
from paperdl.dispatch import adapter_key_for


def test_springer_by_publisher_string():
    assert adapter_key_for("Springer Science and Business Media LLC", "10.1007/x") == "springer"


def test_springer_by_doi_prefix():
    assert adapter_key_for("", "10.1007/s00339-021-04567-w") == "springer"


def test_unknown_publisher_returns_none():
    assert adapter_key_for("Some Tiny Press", "10.9999/x") is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_dispatch.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3: 写实现**

`paperdl/dispatch.py`:
```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_dispatch.py -v`
Expected: PASS（3 passed）。

- [ ] **Step 5: 提交**

```bash
git add paperdl/dispatch.py tests/test_dispatch.py
git commit -m "feat: publisher-to-adapter dispatch"
```

---

### Task 5: results.py — 结果记录与去重

**Files:**
- Create: `paperdl/results.py`
- Create: `tests/test_results.py`

- [ ] **Step 1: 写失败测试**

`tests/test_results.py`:
```python
from paperdl.results import ResultStore, ResultRow


def test_roundtrip_and_completed_set(tmp_path):
    path = tmp_path / "results.csv"
    store = ResultStore(path)
    store.record(ResultRow(doi="10.1/a", publisher="springer", title="T1",
                           status="success", reason="", file_path="downloads/a.pdf"))
    store.record(ResultRow(doi="10.1/b", publisher="springer", title="T2",
                           status="failed", reason="no_pdf", file_path=""))

    reloaded = ResultStore(path)
    assert reloaded.completed_dois() == {"10.1/a"}  # 只有 success 算完成
    assert "10.1/b" not in reloaded.completed_dois()


def test_failed_dois(tmp_path):
    path = tmp_path / "results.csv"
    store = ResultStore(path)
    store.record(ResultRow(doi="10.1/a", publisher="x", title="", status="success",
                           reason="", file_path="downloads/a.pdf"))
    store.record(ResultRow(doi="10.1/b", publisher="x", title="", status="failed",
                           reason="timeout", file_path=""))
    assert ResultStore(path).failed_dois() == ["10.1/b"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_results.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3: 写实现**

`paperdl/results.py`:
```python
import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Set

FIELDS = ["doi", "publisher", "title", "status", "reason", "file_path", "attempted_at"]


@dataclass
class ResultRow:
    doi: str
    publisher: str
    title: str
    status: str  # "success" | "failed"
    reason: str
    file_path: str
    attempted_at: str = ""


class ResultStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._rows: List[dict] = []
        if self.path.exists():
            with self.path.open(newline="", encoding="utf-8") as f:
                self._rows = list(csv.DictReader(f))

    def record(self, row: ResultRow) -> None:
        d = asdict(row)
        if not d["attempted_at"]:
            d["attempted_at"] = datetime.now(timezone.utc).isoformat()
        self._rows.append(d)
        self._flush()

    def _flush(self) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(self._rows)

    def completed_dois(self) -> Set[str]:
        return {r["doi"] for r in self._rows if r["status"] == "success"}

    def failed_dois(self) -> List[str]:
        done = self.completed_dois()
        seen, out = set(), []
        for r in self._rows:
            if r["status"] == "failed" and r["doi"] not in done and r["doi"] not in seen:
                seen.add(r["doi"])
                out.append(r["doi"])
        return out
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_results.py -v`
Expected: PASS（2 passed）。

- [ ] **Step 5: 提交**

```bash
git add paperdl/results.py tests/test_results.py
git commit -m "feat: results store with dedup"
```

---

### Task 6: adapters — 接口与 Springer 的 PDF 链接提取（纯函数）

**Files:**
- Create: `paperdl/adapters/__init__.py`
- Create: `paperdl/adapters/base.py`
- Create: `paperdl/adapters/springer.py`
- Create: `tests/fixtures/springer_article.html`
- Create: `tests/test_springer_extract.py`

- [ ] **Step 1: 写 HTML 夹具**

`tests/fixtures/springer_article.html`（Springer 文章页的典型 PDF 链接结构）:
```html
<!doctype html>
<html>
<head><title>Article</title></head>
<body>
  <article>
    <h1>A study of something interesting</h1>
    <div class="c-pdf-download">
      <a class="c-pdf-download__link"
         href="/content/pdf/10.1007/s00339-021-04567-w.pdf"
         data-track-action="download pdf">Download PDF</a>
    </div>
  </article>
</body>
</html>
```

- [ ] **Step 2: 写失败测试**

`tests/test_springer_extract.py`:
```python
from pathlib import Path

from paperdl.adapters.springer import find_pdf_url

FIX = Path(__file__).parent / "fixtures"


def test_find_pdf_url_resolves_relative_link():
    html = (FIX / "springer_article.html").read_text()
    url = find_pdf_url(html, base_url="https://link-springer-com.proxy.las.ac.cn/article/10.1007/s00339-021-04567-w")
    assert url == "https://link-springer-com.proxy.las.ac.cn/content/pdf/10.1007/s00339-021-04567-w.pdf"


def test_find_pdf_url_returns_none_when_absent():
    assert find_pdf_url("<html><body>no link</body></html>", base_url="https://x.com/a") is None
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_springer_extract.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 4: 写适配器接口与 Springer 提取实现**

`paperdl/adapters/__init__.py`: 空文件。

`paperdl/adapters/base.py`:
```python
from dataclasses import dataclass
from typing import Optional, Protocol

from paperdl.resolver import Metadata


@dataclass
class DownloadResult:
    ok: bool
    pdf_bytes: Optional[bytes] = None
    reason: str = ""  # 失败原因分类: no_access | blocked | no_pdf | timeout | error


class Adapter(Protocol):
    key: str

    def download(self, page, md: Metadata) -> DownloadResult:
        """用已登录的 Playwright page 把 md 对应文章的 PDF 抓下来。"""
        ...
```

`paperdl/adapters/springer.py`:
```python
import re
from urllib.parse import urljoin
from typing import Optional

# 不引入额外 HTML 解析依赖：用正则在 Springer 文章页定位下载链接。
# Springer 的下载链接形如 /content/pdf/<doi>.pdf，class 含 c-pdf-download__link。
_PDF_HREF = re.compile(
    r'href="(?P<href>[^"]*?/content/pdf/[^"]+\.pdf)"', re.IGNORECASE
)


def find_pdf_url(html: str, base_url: str) -> Optional[str]:
    m = _PDF_HREF.search(html)
    if not m:
        return None
    return urljoin(base_url, m.group("href"))
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_springer_extract.py -v`
Expected: PASS（2 passed）。

- [ ] **Step 6: 提交**

```bash
git add paperdl/adapters/ tests/test_springer_extract.py tests/fixtures/springer_article.html
git commit -m "feat: adapter interface and Springer PDF-link extraction"
```

---

### Task 7: session.py — Playwright 持久化会话与 login

**Files:**
- Create: `paperdl/session.py`
- Create: `tests/test_session.py`

说明：Playwright 真实浏览器无法做纯单元测试，因此本任务的自动化测试只覆盖「路径与配置」逻辑，浏览器行为放到 Task 8 的手动验证。

- [ ] **Step 1: 写失败测试**

`tests/test_session.py`:
```python
from pathlib import Path

from paperdl.session import profile_dir, LAS_HOME


def test_profile_dir_is_under_project(tmp_path):
    p = profile_dir(base=tmp_path)
    assert p == tmp_path / ".profile"


def test_las_home_constant():
    assert LAS_HOME.startswith("https://www.las.ac.cn")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_session.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3: 写实现**

`paperdl/session.py`:
```python
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

LAS_HOME = "https://www.las.ac.cn/front/dataCenter/literatureAcquisition"


def profile_dir(base: Optional[Path] = None) -> Path:
    base = Path(base) if base else Path.cwd()
    return base / ".profile"


@contextmanager
def browser_context(headless: bool, base: Optional[Path] = None):
    """打开持久化上下文：登录态(cookie/localStorage)保存在 .profile/ 里复用。"""
    pdir = profile_dir(base)
    pdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(pdir),
            headless=headless,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            yield ctx
        finally:
            ctx.close()


def run_login(base: Optional[Path] = None) -> None:
    """有头打开 las.ac.cn，提示用户手动完成通行证登录与出版商机构登录。"""
    with browser_context(headless=False, base=base) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(LAS_HOME)
        print("浏览器已打开。请在窗口中完成：")
        print("  1) 用中国科技云通行证登录（账号=中科院邮箱），处理验证码/二次验证；")
        print("  2) 点进 Springer（link.springer.com）做一次机构登录，确认能看到全文；")
        print("完成后回到终端按回车保存会话。")
        input("按回车结束登录并保存会话 > ")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_session.py -v`
Expected: PASS（2 passed）。

- [ ] **Step 5: 提交**

```bash
git add paperdl/session.py tests/test_session.py
git commit -m "feat: Playwright persistent session and login flow"
```

---

### Task 8: adapters/springer.py — 导航与下载（集成，手动验证）

**Files:**
- Modify: `paperdl/adapters/springer.py`

说明：本任务给 Springer 适配器加 `download()`，用已登录 page 导航到文章页、提取 PDF 链接、下载字节。需真实登录手动验证，无自动化单测。

- [ ] **Step 1: 在 springer.py 追加 download 实现**

在 `paperdl/adapters/springer.py` 末尾追加（文件顶部 import 区补充 `from paperdl.adapters.base import DownloadResult` 和 `from paperdl.resolver import Metadata`）:
```python
from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata

key = "springer"


def download(page, md: Metadata) -> DownloadResult:
    # md.url 是 dx.doi.org 链接；登录态下让浏览器自己解析到机构代理域。
    try:
        page.goto(md.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")

    html = page.content()
    pdf_url = find_pdf_url(html, base_url=page.url)
    if not pdf_url:
        # 页面里没有下载链接：可能无权限或反爬拦截
        if "login" in page.url.lower() or "shibboleth" in page.url.lower():
            return DownloadResult(ok=False, reason="no_access")
        return DownloadResult(ok=False, reason="no_pdf")

    # 用浏览器上下文的请求拿 PDF（带上登录 cookie）
    try:
        resp = page.request.get(pdf_url, timeout=120000)
    except Exception:
        return DownloadResult(ok=False, reason="timeout")
    if resp.status != 200:
        return DownloadResult(ok=False, reason="no_access")
    body = resp.body()
    if not body[:5].startswith(b"%PDF"):
        return DownloadResult(ok=False, reason="blocked")
    return DownloadResult(ok=True, pdf_bytes=body)
```

- [ ] **Step 2: 跑一遍已有单测确认没破坏提取逻辑**

Run: `pytest tests/test_springer_extract.py -v`
Expected: PASS（2 passed，find_pdf_url 行为不变）。

- [ ] **Step 3: 手动端到端验证（阶段 0 的关键验证）**

先 `paperdl login`（Task 10 完成后）或临时脚本调用 `session.run_login()` 登录。
然后用一个 Springer 真实 DOI 做最小验证脚本 `scratch_verify.py`（验证后删除，不提交）:
```python
from paperdl.session import browser_context
from paperdl.resolver import fetch_metadata
from paperdl.adapters import springer

doi = "10.1007/s00339-021-04567-w"  # 换成你有权限的真实 Springer DOI
md = fetch_metadata(doi)
with browser_context(headless=False) as ctx:
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    r = springer.download(page, md)
    print("ok=", r.ok, "reason=", r.reason, "bytes=", len(r.pdf_bytes or b""))
    if r.ok:
        open("verify.pdf", "wb").write(r.pdf_bytes)
```

Run: `python scratch_verify.py`
Expected: `ok= True`，verify.pdf 能正常打开是真 PDF。
**若失败**：记录 reason，按 reason 调整（no_access→检查机构登录是否在 .profile 生效；no_pdf→保存 page.content() 看真实下载链接结构并修正 `_PDF_HREF` 正则与夹具）。这一步是阶段 0 成败判定点。

- [ ] **Step 4: 清理并提交**

```bash
rm -f scratch_verify.py verify.pdf
git add paperdl/adapters/springer.py
git commit -m "feat: Springer navigate-and-download (verified end-to-end)"
```

---

### Task 9: downloader.py — 主循环（限速/重试/去重/记录）

**Files:**
- Create: `paperdl/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: 写失败测试（用假适配器与假 page，不开真浏览器）**

`tests/test_downloader.py`:
```python
from pathlib import Path

from paperdl.downloader import download_one, DownloadContext
from paperdl.adapters.base import DownloadResult
from paperdl.resolver import Metadata


class FakeAdapter:
    key = "fake"
    def __init__(self, result):
        self._result = result
    def download(self, page, md):
        return self._result


def test_download_one_success_writes_pdf(tmp_path):
    md = Metadata(doi="10.1/a", first_author="Zhang", year=2021, title="T",
                  publisher="Springer")
    adapter = FakeAdapter(DownloadResult(ok=True, pdf_bytes=b"%PDF-1.7 data"))
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={"fake": adapter})
    row = download_one(md, "fake", ctx)
    assert row.status == "success"
    assert (tmp_path / row.file_path).read_bytes().startswith(b"%PDF")


def test_download_one_failure_records_reason(tmp_path):
    md = Metadata(doi="10.1/b", publisher="Springer")
    adapter = FakeAdapter(DownloadResult(ok=False, reason="no_access"))
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={"fake": adapter})
    row = download_one(md, "fake", ctx)
    assert row.status == "failed"
    assert row.reason == "no_access"
    assert row.file_path == ""


def test_download_one_unknown_adapter(tmp_path):
    md = Metadata(doi="10.1/c", publisher="Tiny Press")
    ctx = DownloadContext(page=None, out_dir=tmp_path, adapters={})
    row = download_one(md, None, ctx)
    assert row.status == "failed"
    assert row.reason == "no_adapter"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_downloader.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3: 写实现**

`paperdl/downloader.py`:
```python
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from paperdl.adapters.base import Adapter
from paperdl.naming import build_filename
from paperdl.resolver import Metadata, fetch_metadata
from paperdl.dispatch import adapter_key_for
from paperdl.results import ResultRow, ResultStore

DELAY_MIN = 8
DELAY_MAX = 20
MAX_PER_RUN = 50
RETRIES = 2


@dataclass
class DownloadContext:
    page: object
    out_dir: Path
    adapters: Dict[str, Adapter]
    delay_min: float = DELAY_MIN
    delay_max: float = DELAY_MAX


def download_one(md: Metadata, adapter_key: Optional[str], ctx: DownloadContext) -> ResultRow:
    if adapter_key is None or adapter_key not in ctx.adapters:
        return ResultRow(doi=md.doi, publisher=md.publisher, title=md.title,
                         status="failed", reason="no_adapter", file_path="")
    adapter = ctx.adapters[adapter_key]
    result = adapter.download(ctx.page, md)
    if not result.ok:
        return ResultRow(doi=md.doi, publisher=md.publisher, title=md.title,
                         status="failed", reason=result.reason, file_path="")
    ctx.out_dir.mkdir(parents=True, exist_ok=True)
    fname = build_filename(md)
    (ctx.out_dir / fname).write_bytes(result.pdf_bytes)
    return ResultRow(doi=md.doi, publisher=md.publisher, title=md.title,
                     status="success", reason="", file_path=fname)


def read_doi_list(path: Path) -> List[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        doi = line.strip().split(",")[0].strip()  # 容忍 csv：取第一列
        if doi and not doi.lower().startswith("doi"):  # 跳过表头
            out.append(doi)
    return out


def run(list_path: Path, ctx: DownloadContext, store: ResultStore,
        max_per_run: int = MAX_PER_RUN) -> None:
    dois = read_doi_list(list_path)
    done = store.completed_dois()
    todo = [d for d in dois if d not in done]
    if len(todo) > max_per_run:
        print(f"清单 {len(todo)} 篇超过单次上限 {max_per_run}，本次只处理前 {max_per_run} 篇，"
              f"其余请下次再跑（已成功的会自动跳过）。")
        todo = todo[:max_per_run]

    for i, doi in enumerate(todo, 1):
        md = fetch_metadata(doi)
        akey = adapter_key_for(md.publisher, md.doi)
        print(f"[{i}/{len(todo)}] {doi} -> {akey or '无适配器'}  {md.title[:50]}")
        row = None
        for attempt in range(1, RETRIES + 2):
            row = download_one(md, akey, ctx)
            if row.status == "success" or row.reason in ("no_adapter",):
                break
            if attempt <= RETRIES:
                back = 2 ** attempt
                print(f"   失败({row.reason})，{back}s 后重试 {attempt}/{RETRIES}")
                time.sleep(back)
        store.record(row)
        print(f"   => {row.status} {row.reason}")
        if i < len(todo):
            time.sleep(random.uniform(ctx.delay_min, ctx.delay_max))

    rows_done = store.completed_dois()
    print(f"完成。成功累计 {len(rows_done)} 篇；失败明细见 results.csv。")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_downloader.py -v`
Expected: PASS（3 passed）。

- [ ] **Step 5: 提交**

```bash
git add paperdl/downloader.py tests/test_downloader.py
git commit -m "feat: download main loop with rate-limit, retry, dedup"
```

---

### Task 10: cli.py — 串起 login / run / retry

**Files:**
- Create: `paperdl/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: 写失败测试（解析层，不开浏览器）**

`tests/test_cli.py`:
```python
from paperdl.cli import build_parser


def test_parser_login():
    args = build_parser().parse_args(["login"])
    assert args.command == "login"


def test_parser_run_requires_list():
    args = build_parser().parse_args(["run", "mylist.txt"])
    assert args.command == "run"
    assert args.list == "mylist.txt"


def test_parser_run_max_option():
    args = build_parser().parse_args(["run", "l.txt", "--max", "10"])
    assert args.max == 10


def test_parser_retry():
    args = build_parser().parse_args(["retry"])
    assert args.command == "retry"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3: 写实现**

`paperdl/cli.py`:
```python
import argparse
import tempfile
from pathlib import Path

from paperdl.downloader import DownloadContext, run, MAX_PER_RUN
from paperdl.results import ResultStore
from paperdl.session import browser_context, run_login
from paperdl.adapters import springer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="paperdl", description="按 DOI 清单批量下载文献")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="打开浏览器手动登录并保存会话")

    pr = sub.add_parser("run", help="按清单下载")
    pr.add_argument("list", help="DOI 清单文件（txt/csv，每行一个 DOI 或第一列为 DOI）")
    pr.add_argument("--max", type=int, default=MAX_PER_RUN, help="单次上限")
    pr.add_argument("--headless", action="store_true", help="无头运行（先确认会话可用再用）")

    sub.add_parser("retry", help="仅重试上次失败的条目")
    return p


# 已注册的适配器（阶段 0 只有 springer）
ADAPTERS = {"springer": springer}


def _do_run(list_path: str, max_per_run: int, headless: bool) -> None:
    store = ResultStore(Path("results.csv"))
    with browser_context(headless=headless) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        dctx = DownloadContext(page=page, out_dir=Path("downloads"), adapters=ADAPTERS)
        run(Path(list_path), dctx, store, max_per_run=max_per_run)


def _do_retry() -> None:
    store = ResultStore(Path("results.csv"))
    failed = store.failed_dois()
    if not failed:
        print("没有需要重试的失败条目。")
        return
    tmp = Path(tempfile.mkstemp(suffix=".txt")[1])
    tmp.write_text("\n".join(failed), encoding="utf-8")
    _do_run(str(tmp), max_per_run=len(failed), headless=False)
    tmp.unlink(missing_ok=True)


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "login":
        run_login()
    elif args.command == "run":
        _do_run(args.list, args.max, args.headless)
    elif args.command == "retry":
        _do_retry()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS（4 passed）。

- [ ] **Step 5: 全套测试 + 手动冒烟**

Run: `pytest -v`
Expected: 全部 PASS。

手动冒烟（需你本人登录）:
```bash
python -m paperdl login          # 浏览器登录通行证 + Springer 机构登录
printf '10.1007/s00339-021-04567-w\n' > mylist.txt   # 换成你有权限的真实 Springer DOI
python -m paperdl run mylist.txt
ls downloads/                    # 应出现下载的 PDF
cat results.csv                  # 状态为 success
```

- [ ] **Step 6: 提交**

```bash
git add paperdl/cli.py tests/test_cli.py
git commit -m "feat: CLI with login/run/retry subcommands"
```

---

## 自查：spec 覆盖核对

- 输入 DOI 清单(txt/csv) → Task 9 `read_doi_list`（容忍 csv、跳表头）。✓
- Crossref 元数据解析 → Task 2。✓
- Playwright 持久化会话 + 手动登录、不存密码 → Task 7。✓
- 按出版商分发 → Task 4。✓
- 适配器（阶段 0=Springer）：提取纯函数 + 导航下载 → Task 6、8。✓
- 主循环：去重/限速(8–20s)/单次上限(50)/指数退避重试(2 次)/results.csv 分类原因 → Task 9。✓
- 文件名 = 一作-年份-标题截断，非法字符清洗 → Task 3。✓
- CLI：login/run/retry → Task 10。✓
- 阶段 0 关键验证「会话能脚本化下到 PDF」→ Task 8 Step 3 手动端到端。✓

阶段 1+（Elsevier 等其余出版商、国内库、文献传递兜底）按 spec 留待阶段 0 验证通过后另出计划。
