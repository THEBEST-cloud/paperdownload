# OpenAlex 文献检索 — 设计

日期:2026-06-23
状态:已设计,待实现

## 背景与目标

paperdl 现在只能"按 DOI 清单批量下载",缺少**按关键词检索发现文献**的前段能力(las.ac.cn 无统一全文检索框)。本功能补上类似谷歌学术结果页的体验:输入关键词 → 列出相关论文(标题/作者/年/被引/摘要/OA)→ 可筛选 → 人工挑选后**勾选送入现有下载流程**或导出清单。

定位是 **B(文献调研工具)**:检索 + 浏览 + 筛选为主,下不下载由人决定;搜到结果后能一键衔接现有下载(**A 桥接**)。

## 范围

做:
- OpenAlex 单一检索源,可插拔架构(WoS 等以后可加)。
- CLI `paperdl search` 命令。
- 网页版检索页:结果列表 + 筛选 + 勾选下载 + 导出。
- 导出格式:DOI 清单 / CSV / BibTeX。

不做(YAGNI):
- WoS 接入(无 API key;预留可插拔接口,以后有 key 再加)。
- 不爬 Google Scholar / WoS 网页 SPA(反爬+合规风险)。
- 收藏夹 / 账号级检索历史同步。

## 数据源:为什么是 OpenAlex

- Google Scholar 无公开 API 且反爬极严,与项目"合规限速、别封 IP"红线冲突 → 不用。
- WoS 官方 API 需机构 key(图书馆管控,个人不一定有);网页 SPA 爬取脆弱+ToS 风险 → 第一版不做,留可插拔接口。
- OpenAlex:免费、无需 key、全学科 2.5 亿+、含标题/作者/年/被引/摘要/OA/出版商,筛选强,直接给 DOI → 无缝接现有下载。选它。

## 架构:可插拔检索源

新建 `paperdl/search/` 模块,仿照下载端"多适配器"思路:

- `base.py`
  - `@dataclass Paper`:`title, authors(list[str]), year(int|None), venue(str), doi(str|None), cited_by(int), is_oa(bool), abstract(str), type(str), oa_url(str|None)`。
  - `@dataclass SearchPage`:`results(list[Paper]), total(int), page(int), per_page(int)`。
  - `@dataclass SearchQuery`:`query, year_from, year_to, oa_only, work_type, sort, page, per_page`。
  - `class SearchSource(Protocol)`:`search(q: SearchQuery) -> SearchPage`。
- `openalex.py`:`OpenAlexSource` 实现。拼 API 参数、还原倒排索引摘要、字段映射为 `Paper`。
- `__init__.py`:源注册表 + `get_source(name="openalex")`。

网页与 CLI 都依赖 `SearchSource` 抽象;新增源不动上层。

## OpenAlex 接入细节

- 端点:`GET https://api.openalex.org/works`。无需 key。
- **礼貌池**:带 `mailto=` 参数,值取配置邮箱(`.paperdl.env` 里复用已有邮箱配置;没配则匿名)。合规、稳定。
- **摘要还原**:`abstract_inverted_index` → 正常文本(按 position 还原)。
- **检索参数映射**:
  - 关键词:`search=`。
  - 年份区间:`filter=from_publication_date:YYYY-01-01,to_publication_date:YYYY-12-31`(或 `publication_year`)。
  - OA:`filter=is_oa:true`。
  - 类型:默认 `filter=type:article`。
  - 排序:相关度(默认,`relevance_score`)/ 被引(`cited_by_count:desc`)/ 年份(`publication_date:desc`)。
  - 翻页:`page=` + `per-page=`(默认 25,上限 200)。
- **限速**:OpenAlex 宽松,仍加轻量节流(单次请求间最小间隔),与项目红线一致。
- **错误处理**:网络错误/非 200 → 抛带消息的异常,上层(CLI 打印、Web 返回 4xx/5xx)友好提示;空结果返回 `SearchPage(results=[], total=0)`。

## CLI:`paperdl search`

```
paperdl search "microplastics drinking water" --from 2020 --to 2025 --oa --sort cited -n 25
paperdl search "..." -o list.txt     # 导出 DOI 清单(直接喂 paperdl run)
paperdl search "..." --csv out.csv   # 导出 CSV
paperdl search "..." --bib out.bib   # 导出 BibTeX
```

- 参数:`query`(位置)、`--from/--to`(年份)、`--oa`、`--sort {relevance,cited,year}`、`-n/--num`(数量)、`--type`、`-o/--out`(DOI 清单)、`--csv`、`--bib`。
- 不带导出参数:终端打印结果表(序号/标题/作者/年/被引/OA/DOI)。
- 带导出参数:写文件;`-o` 产出的清单可直接 `paperdl run list.txt`。
- 注册到 `paperdl/cli.py` 的 subparser;`pyproject.toml` 已有 `paperdl` 入口,无需改。

## 网页版:检索页

- `index.html` 单页里加"检索"视图(与现有下载视图切换)。
- 顶部搜索框 + 侧边筛选(年份区间、仅 OA、类型、排序下拉)。
- 结果区:表格/卡片列出 标题、作者、年、来源、被引、OA 徽章、摘要(可展开);每条带勾选框。
- 翻页 / "加载更多"。
- 底部操作条:
  - **「下载选中」**:把勾选 DOI 灌进现有下载流程(复用 `paperdl/web/jobs.py` 的 JobManager,等价于粘贴 DOI 提交)。
  - **「导出」**:DOI 清单 / CSV / BibTeX 下载。
- 后端 FastAPI 路由(`paperdl/web/app.py`):
  - `GET /api/search`:参数同 CLI,返回 `SearchPage` JSON。
  - `POST /api/search/export`:body 给 DOI 列表 + 格式,返回文件。
  - 下载衔接:勾选 DOI → 复用现有创建下载任务的接口(不新造下载逻辑)。

## 导出格式

- **DOI 清单**:纯文本每行一个 DOI(与 `paperdl run` 输入兼容)。
- **CSV**:title, authors, year, venue, doi, cited_by, is_oa, type。
- **BibTeX**:由 `Paper` 字段生成 `@article{...}`(key 用 第一作者姓+年+短词)。

## 测试

- `tests/` 下加 `test_search_openalex.py` 等,与现有 pytest 一致:
  - 用**录制的 OpenAlex 响应 fixture**(不打真网):字段映射、倒排索引摘要还原、检索参数拼装(年份/OA/排序/类型)、空结果、HTTP 错误。
  - CLI 三种导出格式各一个单测(DOI 清单 / CSV / BibTeX 内容正确)。
  - Web 路由:用 FastAPI TestClient + mock 的 source,验证 `/api/search` 返回结构、`/api/search/export` 产物。

## 实现后

- 更新 `README.md`:新增"检索"小节(CLI + 网页用法),并在顶部能力清单提一句"按关键词检索(OpenAlex)";结构说明里补 `paperdl/search/`。
- `scripts/make_skill.py` 白名单按需带上 `paperdl/search/`(若有显式文件清单)。
