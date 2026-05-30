# paperdl — 按 DOI 清单批量下载文献（设计文档）

- 日期：2026-05-30
- 状态：已与用户确认，待写实现计划
- 适用环境：中科院文献情报中心（las.ac.cn）统一资源访问，登录用中国科技云通行证（CSTCloud passport，Shibboleth/OAuth2，账号为中科院邮箱）

## 1. 背景与约束

用户是中科院某所人员，通过 `https://www.las.ac.cn/front/dataCenter/literatureAcquisition`
访问机构订阅资源。实际取全文流程为：**登录中国科技云通行证 → 点进具体出版商数据库
（如 ScienceDirect）→ 在库内检索 → 下载 PDF**。las.ac.cn 没有"一个搜索框直接出全文"
的统一入口；全文权限靠登录后的联邦认证让出版商识别"中科院"机构身份。

由此引出三条硬约束：

1. **无法做通用"任意 DOI 一键出 PDF"入口**，必须按出版商分别适配（各家文章页结构、
   PDF 链接、反爬机制不同）。
2. **登录环节复杂**：中国科技云通行证大概率含验证码、密码 JS 加密、可能二次验证，
   纯 HTTP 模拟登录脆弱且易触发风控 → 采用真实浏览器（Playwright），用户手动登录一次。
3. **合规与风控**：出版商禁止批量爬取/整刊下载；触发风控可能导致机构 IP 段被封，
   影响全所访问。脚本必须按用户给定清单逐篇、带合理间隔下载，并设单次上限。

## 2. 目标 / 非目标

**目标**
- 输入一份 DOI 清单（txt/csv），逐篇下载到本地，文件名可读，并产出成功/失败明细。
- 对验证码、JS 加密登录、Shibboleth 跳转、出版商反爬具备实用鲁棒性。
- 限速、断点续传、失败重试、不存储用户密码。

**非目标**
- 不做关键词检索批量抓取（最接近爬虫、风险最高，明确排除）。
- 不自动化破解验证码或二次验证（由用户手动完成登录）。
- 不追求一次性覆盖全部出版商；按需分阶段铺开。

## 3. 整体架构

单机命令行工具，技术栈 Python + Playwright + Crossref API。

```
DOI清单(txt/csv)
   │
   ▼
[1 元数据解析]  Crossref API  →  出版商、期刊、标题、作者年份、文章页URL
   │
   ▼
[2 会话管理]   Playwright 持久化浏览器 profile（本地）
               · 一次性 `paperdl login`：手动登录通行证 + 各出版商机构登录
               · 之后复用已登录 cookie
   │
   ▼
[3 分发器]     按出版商把 DOI 路由到对应适配器
   │
   ▼
[4 出版商适配器]  每家一个模块：导航到文章页 → 定位 PDF 链接 → 下载
   │
   ▼
[5 输出]       PDF → ./downloads/，文件名 = 一作-年份-标题截断.pdf
               results.csv 记录每个 DOI：成功/失败/原因
```

## 4. 组件与职责

- **`resolver.py`** — DOI → 元数据。仅调 Crossref（免费、礼貌限速、带 User-Agent 邮箱）。
  解析失败的 DOI 标记后跳过，不中断整体。
- **`session.py`** — 管理 Playwright 持久化 profile。`login` 子命令开有头浏览器供手动登录；
  下载时复用同一 profile（可无头）。只保存浏览器会话 cookie，**不保存账号密码**。
- **`adapters/`** — 每家出版商一个文件（`springer.py`、`elsevier.py`、`wiley.py`、`nature.py`、
  `acs.py`、`rsc.py`、`ieee.py`、`iop.py`、`aps.py`、`cnki.py`、`wanfang.py`、`vip.py`）。
  统一接口：输入 DOI + 元数据 + 已登录 page，输出 PDF 字节或结构化失败原因。
- **`downloader.py`** — 主循环。读清单 → 去重（已下跳过）→ 逐条调适配器 → 随机间隔 →
  指数退避重试 → 写 results.csv。
- **`cli.py`** — 子命令：
  - `paperdl login`：打开浏览器手动登录。
  - `paperdl run <list.txt>`：执行下载。
  - `paperdl retry`：只重试上次 results.csv 中失败的条目。

## 5. 分阶段落地

最大未知是"CAS 联邦登录会话能否脚本化下到 PDF"。在验证前不写多家适配，避免浪费。

- **阶段 0（先做，验证可行性）**：搭框架 + 仅做 **Springer**（页面最规范、最易跑通）。
  目标：证明登录会话可脚本化下载。此步不过，后续全部作废。
- **阶段 1**：加 **Elsevier/ScienceDirect**（需求最大、最难、反爬最重）。
- **阶段 2**：Wiley、Nature、ACS、RSC、IEEE、IOP、APS。
- **阶段 3**：国内库 CNKI / 万方 / 维普（登录与下载机制不同，单独处理）。
- **兜底**：始终下不动的出版商走"文献传递"（中科院 NSTL 文献传递，提交请求由馆方
  取全文发邮箱），或在 results.csv 标出供用户手动处理。

## 6. 健壮性与风控

- **限速**：每篇之间随机停 **8–20 秒**；单次运行默认上限 **50 篇**，超出提示分批。两值可配置。
- **断点续传**：results.csv 记录状态，重跑自动跳过已成功条目。
- **重试**：失败按指数退避重试 2 次；仍失败则记录分类原因
  （无权限 / 反爬拦截 / 找不到 PDF / 超时 / 元数据解析失败）。
- **可观察**：实时打印进度；结束输出汇总（成功 N、失败 M 及分类）。
- **凭证安全**：不存储账号密码；登录由用户在浏览器中手动完成，仅本地保存会话 cookie。

## 7. 数据 / 文件布局

```
paperdownload/
├── paperdl/                 # 源码包
│   ├── cli.py
│   ├── resolver.py
│   ├── session.py
│   ├── downloader.py
│   └── adapters/
├── downloads/               # 下载的 PDF（git 忽略）
├── .profile/                # Playwright 持久化 profile（git 忽略，含会话 cookie）
├── results.csv              # 下载明细（git 忽略）
└── docs/superpowers/specs/  # 设计文档
```

- `results.csv` 字段：`doi, publisher, title, status, reason, file_path, attempted_at`
- 文件名清洗：去非法字符，标题截断到约 80 字符。

## 8. 待实现阶段澄清的开放问题

- Springer 经 CAS 机构登录后，文章页 PDF 链接的确切选择器（阶段 0 实测确定）。
- 各出版商是否需每次单独触发 Shibboleth "机构登录"，还是一次登录全站通用
  （阶段 0/1 实测确定）。
- 国内库（CNKI 等）的登录入口与下载按钮形态（阶段 3 实测确定）。
