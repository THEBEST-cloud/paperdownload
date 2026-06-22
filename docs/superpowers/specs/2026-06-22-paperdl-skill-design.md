# paperdl → 可分享 Skill 设计（中科院专用）

- 日期：2026-06-22
- 状态：待评审
- 背景参考：scansci-pdf（Apache-2.0）的范式——SKILL.md 写法、MCP 编排、config/doctor 分层

## 目标

把 paperdl 打磨成一个**自包含、可拷给同事/换机器、能自己配账号**的 Claude Code skill。
新增 4 个能力 + 脱敏打包成 skill：

1. `paperdl config` —— 交互式配置向导（自己配账号，核心诉求）
2. `paperdl doctor` —— 一键环境/状态自检
3. 干净打包 + 一键 setup（换机器可复现）
4. `paperdl mcp` —— MCP server（给任意 AI agent 调，**最后做**）
5. 脱敏打包成 skill（SKILL.md 借鉴 scansci 结构）

## 非目标（明确不做）

- **通用化**：不做跨机构（CARSI/EZProxy/WebVPN 表）、不做通用 PDF 路由、不做数据驱动出版商表。**只服务中科院 CSTCloud 通行证这一条路。**（保留：把机构相关常量集中放一处、带 CAS 默认值，便于以后改，但不抽象成通用框架。）
- 不做 arXiv / 关键词搜索 / Sci-Hub / LibGen / Tor / Docker。
- 不改现有 13 个适配器的下载逻辑（除非 setup/打包必要）。

## 现状（不动的核心）

- `paperdl/` 包：cli / session(patchright+Xvfb+CSTCloud 自动登录+短信绑定) / shibboleth / downloader / adapters(13 家) / web(FastAPI+前端) / mailer / 等。
- 凭证读自 gitignore 的 `.paperdl.env`；登录态存 `.profile/`。
- 运行环境：`/home/hoo/.conda/envs/res-agent`（patchright + chromium 1223 + 系统 xvfb）。

## 组件设计

### 1. `paperdl config` — 配置向导

- 新增 CLI 子命令 `config`（`cli.py` 加分支 + `paperdl/configure.py`）。
- 逐项交互写入 `.paperdl.env`（基于 `.paperdl.env.example` 模板）：
  - 必填：`CSTCLOUD_ID`、`CSTCLOUD_PASSWORD`
  - 选填（带"如何申请"提示）：`ELSEVIER_API_KEY`、`ELSEVIER_INSTTOKEN`、`WILEY_TDM_TOKEN`、`SMTP_HOST/PORT/USER/PASSWORD/FROM/SSL`
- 行为：已存在则按键增量更新（保留未涉及项）；密码用 `getpass` 不回显；不打印/记录任何值；写完 `chmod 600`。
- **绝不内置任何人的真实值**；模板只有注释 + 空值。

### 2. `paperdl doctor` — 自检

- 新增 CLI 子命令 `doctor`（`paperdl/doctor.py`），逐项 ✅/⚠️/❌ + 修复提示：
  - Python 依赖可导入（patchright/httpx/fastapi/...）
  - patchright chromium 是否已安装（`patchright install chromium`）
  - xvfb 可用 / DISPLAY
  - `.paperdl.env` 存在 + 必填项齐
  - **代理泄漏检查**（环境变量 http_proxy/https_proxy/all_proxy 是否设置——设了会让浏览器走境外、破坏 CSTCloud/Shibboleth 登录，应提示清除；机构访问靠 Shibboleth 而非 IP，故只警告代理、不要求"机构 IP"）。另直连查一次出口 IP 仅作信息展示。
  - 登录态：`.profile/` 是否存在、通行证会话是否有效（轻量，不重复触发风控）
  - 限流轻探（可选，默认跳过，避免戳 SD）
- 退出码：全绿 0，有 ❌ 非 0（便于脚本判断）。

### 3. 打包 + 一键 setup

- `pyproject.toml`：console 入口 `paperdl = paperdl.cli:main`；依赖从现有 `requirements.txt` 收敛并 pin。
- `scripts/setup.sh`：建独立 venv（或 uv）→ `pip install -e .` → `patchright install chromium` → 检查/提示 xvfb（`sudo apt install -y xvfb`）。
- 运行产物（`.paperdl.env`/`.profile`/`downloads`/`web_data`/`results.csv`）放工作目录，不进 skill 包。

### 4. `paperdl mcp` — MCP server（最后做）

- 用 `mcp`(FastMCP) 暴露少量工具：`download_dois(dois)`、`download_list(path)`、`config_status()`、`doctor()`、`job_status()`。
- 复用 `downloader` + `browser_context`（同网页任务，跑在 Xvfb 浏览器）。
- 可选依赖（`pip install paperdl[mcp]`），不装也不影响 CLI/web。

### 5. 脱敏打包成 skill

- 位置：个人目录 `~/.claude/skills/paperdl/`（最简单，可直接拷给同事；不做 plugin）。
- 结构：
  ```
  paperdl/
    SKILL.md            # 借鉴 scansci 结构：能力矩阵 + 命令参考 + 工作流配方 + 边界 + 排障 + 安装引导
    app/                # 脱敏后的 paperdl 源码副本（pyproject/paperdl/scripts/tests/requirements）
    references/
      troubleshooting.md   # 代理坑/限流/短信/Shibboleth 各家坑（从记忆与本仓库经验整理）
      env.example          # 带注释、无值的 .paperdl.env 模板
  ```
- **脱敏（打包脚本强制排除/清理）**：`.paperdl.env`、`.profile/`、`downloads/`、`web_data/`、`results.csv`、`*.csv`、`.git/`、`__pycache__/`、`.profile_*`；并扫描 `docs/`、`CLAUDE.md`、注释里是否残留个人邮箱/账号/手机号并清掉。
- SKILL.md 触发描述（中英关键词）：下文献/DOI/批量下载/配置账号/中科院/CSTCloud 等。
- 机构相关常量（passport URL、las 入口匹配 ENTRY_MATCH）集中放一处并注明"中科院默认，改这里可换单位"——仅注释级，不做通用框架。

## 分期

1. **阶段一（先可用）**：① config + ② doctor + ③ 打包/setup + ⑤ skill 打包（含 SKILL.md、脱敏脚本、references）。交付：同事拿到能一键装+自己配账号+自检+跑下载。
2. **阶段二**：④ MCP server。

## 安全

- 任何真实密钥/会话都不进 skill 包（脱敏脚本 + `.gitignore` 双保险）。
- 每用户配自己的 `.paperdl.env`，`chmod 600`，向导不回显/不记录。
- 合规红线沿用：限速 8–20s/篇、单次上限、不批量爬、不做 Sci-Hub。

## 测试

- `config`：单测写入/增量更新/不覆盖未涉及项（用临时 env 文件）。
- `doctor`：单测各检查项的判定逻辑（mock 掉网络/进程探测）。
- 打包：`pip install -e .` 后 `paperdl --help` / `paperdl config --help` / `paperdl doctor` 可跑。
- 脱敏脚本：单测产物里**不含**任何排除项（断言无 `.paperdl.env`/`.profile` 等）。
- MCP（阶段二）：工具 schema + 一次 download_dois 冒烟。
