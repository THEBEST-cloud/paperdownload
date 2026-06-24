# paperdl

按 DOI 清单批量下载文献的工具（命令行 + 网页版）。面向**中科院**用户，通过中科院文献情报中心（las.ac.cn / 中国科技云通行证 CSTCloud）的机构订阅取全文。

- **覆盖 13 家主流出版商** + 两个开放获取兜底，订阅墙和 Cloudflare 都能过。
- **按关键词检索文献**（OpenAlex，可筛选 / 导出 / 勾选直接下载）。
- **账号密码只存本地** gitignore 的 `.paperdl.env`，不上传、不进代码库。
- 命令行批量跑，或网页版点点鼠标。

---

## 它是怎么取到全文的

机构访问**靠中科院通行证的 Shibboleth 联邦登录**（不是靠 IP）。难点是出版商普遍套了 Cloudflare 反爬，普通 HTTP 客户端即便带着有效 cookie 也会被 TLS 指纹识别而 403。paperdl 的做法：

- **patchright**（隐身版 Chromium）过 Cloudflare 的 "Just a moment" 挑战；
- 走通行证 **Shibboleth** 拿机构授权（含 Atypon 两步同意、Elsevier 的 id.elsevier OAuth 中转等坑都填平了）；
- PDF 一律**通过浏览器自身下载/取字节**（指纹与 cf_clearance 一致），而非 Python 直连。

部分出版商有更快的官方通道（Elsevier API、Wiley TDM），配了 key 就优先走；没配则自动走浏览器。开放获取的文章用 Unpaywall / Crossref 兜底。

### 支持的出版商

| 取全文方式 | 出版商（DOI 前缀） |
|---|---|
| Shibboleth 浏览器（机构订阅） | Elsevier `10.1016`、Wiley `10.1002/10.1111/10.1029`、Nature `10.1038`、Science `10.1126`、ACS `10.1021`、IEEE `10.1109`、Annual Reviews `10.1146` |
| 浏览器 / IP 直通 | Springer `10.1007`、RSC `10.1039` |
| 开放获取（无需登录） | Frontiers `10.3389`、PNAS `10.1073`、AIMS `10.3934`、MDPI `10.3390` |
| 兜底 | Crossref / Unpaywall（任意 OA 可得的文章） |

> 注：能否下到全文取决于**你机构的订阅范围**。机构没订的（如某些老回溯卷）会失败，需走馆际互借 / NSTL 文献传递。

---

## 用 Docker 跑（推荐分享 / 跨平台）

容器内永远是 Linux + 内置 Xvfb，**macOS/Windows 只要装 Docker Desktop 就能用**，无需任何系统适配。所有持久化数据落在 `./data`。

```bash
# 0. 构建镜像（把宿主已下好的 patchright Chromium 烤进去；首次构建）
bash scripts/docker-build.sh

# 1. 首次配置 + 登录（交互式，各做一次）
mkdir -p data
docker compose run --rm -it paperdl config    # 填你自己的通行证账号/密钥
docker compose run --rm -it paperdl doctor     # 自检
docker compose run --rm -it paperdl login      # 一次性短信登录，会话存进 ./data/.profile

# 2. 日常用
docker compose up -d                                  # 网页版 http://<本机>:8200
docker compose run --rm paperdl run /data/list.txt    # 命令行批量（清单放 ./data/list.txt）
```

分享给同事：`docker save paperdl:latest | gzip > paperdl.tar.gz`，对方 `docker load < paperdl.tar.gz` 即可，**无需重新 build**。每人用自己的 `./data`（配自己的账号、做自己的一次性登录）。

> 已验证：**OA 文献**（MDPI 等）在容器内能过 Cloudflare 正常下载。**订阅文献**（Elsevier/ACS 等）需先在容器内 `paperdl login` 建立受信任会话——和新机器流程一样；首次登录后即可。

## 安装（不用 Docker，直接装在 Linux 上）

```bash
bash scripts/setup.sh
```

脚本会：建独立虚拟环境 `.venv` → 装 paperdl 及依赖 → `patchright install chromium` → 检查 Xvfb（无图形界面的服务器需要：`sudo apt-get install -y xvfb`）。

装好后命令是 `paperdl`（或 `.venv/bin/paperdl`）。

---

## 快速上手（命令行）

```bash
paperdl config      # ① 交互式填账号/密钥，生成 .paperdl.env（只填你自己的）
paperdl doctor      # ② 一键自检：依赖/chromium/xvfb/配置/代理/登录态
paperdl login       # ③ 首次登录（陌生设备会要一次性短信验证；之后约 10 天免登录）
paperdl run list.txt # ④ 按清单批量下载
```

- **`paperdl config`**：逐项引导。必填**中科院通行证账号/密码**；Elsevier API key、Wiley TDM token、SMTP 邮件等都是**可选**（留空就走浏览器/不用邮件）。密码不回显、文件 `chmod 600`、绝不内置任何人的默认值。
- **`paperdl doctor`**：新机器或出问题时先跑它，逐项 ✅/⚠️/❌ 给修复提示。
- **`paperdl login`**：弹浏览器自动用 `.paperdl.env` 登录通行证；弹验证码/机构二次登录时按提示点一下。
- **`paperdl run list.txt`**：清单为纯文本每行一个 DOI（兼容 csv 取第一列、跳表头）。默认单次上限 50、每篇间隔 8–20 秒（合规限速，别去掉）。PDF 存 `downloads/`，每篇结果记 `results.csv`，重复跑自动跳过已成功的。

### `.paperdl.env` 长这样（通行证账号 / 密钥示例）

`paperdl config` 会引导你生成它，也可以照 `.paperdl.env.example` 自己手填。**只有通行证账号 + 密码是必填**，其余密钥都可选：

```ini
# 必填——中国科技云通行证（账号就是你登录 passport.escience.cn 用的中科院邮箱）
CSTCLOUD_ID=zhangsan@mails.ucas.ac.cn
CSTCLOUD_PASSWORD=你的通行证登录密码

# 以下全部可选，留空即走浏览器/不发邮件，不影响下载
ELSEVIER_API_KEY=         # 出版商密钥示例：dev.elsevier.com 免费申请，Elsevier 走官方 API 更快
WILEY_TDM_TOKEN=          # Wiley TDM 令牌（onlinelibrary.wiley.com 申请）
OPENALEX_MAILTO=          # 检索用的礼貌池邮箱，留空自动回退用 CSTCLOUD_ID
```

> - **账号 = 你的中科院邮箱**（如 `xxx@mails.ucas.ac.cn` / 各所 `@xxx.ac.cn`），就是平时登 las.ac.cn / 通行证那个；**不是**手机号。
> - **密钥**指的是上面那几个**出版商 API key**，是「锦上添花」的可选项，不是登录通行证用的——通行证只认账号 + 密码。
> - 该文件已被 git 忽略、`chmod 600`，**不会上传、不进代码库**；换机器各自填各自的。

```bash
paperdl run list.txt --max 10   # 自定义单次上限
paperdl retry                   # 只重试上次失败的条目
```

清单示例：
```
10.1016/j.watres.2021.117056
10.1126/science.aap8826
10.3390/atmos15111345
```

---

## 检索文献（OpenAlex）

数据源 **OpenAlex**（免费、无需 key、全学科）；检索结果返回 DOI，可直接交给 `paperdl run` 下载；WoS 等以后可作为可插拔源加入（`paperdl/search/`）。

### 命令行

```bash
# 检索并在终端打印结果表格
paperdl search "microplastics drinking water" --from 2020 --oa --sort cited -n 25

# 导出 DOI 清单，直接 paperdl run list.txt 批量下载
paperdl search "microplastics drinking water" -o list.txt

# 同时导出 CSV 和 BibTeX
paperdl search "microplastics drinking water" --csv out.csv --bib out.bib
```

**常用参数：**

| 参数 | 说明 |
|---|---|
| `--from YYYY` / `--to YYYY` | 发表年份范围 |
| `--oa` | 仅显示开放获取文献 |
| `--sort relevance\|cited\|year` | 排序方式（相关度 / 被引量 / 年份） |
| `--type article` | 文献类型（默认 article） |
| `-n N` | 返回结果数（最多 200） |
| `-o list.txt` | 导出 DOI 清单（可直接接 `paperdl run`） |
| `--csv out.csv` | 导出 CSV |
| `--bib out.bib` | 导出 BibTeX |

### 网页版检索

在「**检索**」页（与「下载」页切换）输入关键词 → 按年份 / 仅 OA / 排序筛选 → 结果卡片显示标题 / 作者 / 年份 / 期刊 / 被引量 / OA 徽标 / 可展开摘要 → 勾选论文后点「**下载选中**」直接进下载队列，或点「**导出**」下载 DOI 清单 / CSV / BibTeX。

---

## 网页版（推荐日常用）

```bash
paperdl serve --host 0.0.0.0 --port 8200
```

浏览器打开后：粘贴 DOI 或上传 Excel/txt → 解析 → 开始下载 → 实时进度表（每篇状态/原因）→ 成功的可预览/下载 PDF → 失败的有「🔄 重试」→ 任务被中断后有「▶️ 继续下载」续跑剩余 → 打包 ZIP / 发到邮箱；左侧有历史任务。复用 `.paperdl.env` / `.profile`，无需在网页里重填。多人使用支持各自账号登录。

> 服务器无图形界面时，本地用 SSH 端口转发再开浏览器：
> `ssh -L 8200:localhost:8200 用户@服务器`，本地访问 http://localhost:8200
> （本地浏览器若配了代理，给 localhost 加直连/绕过规则）。

---

## 失败原因（results.csv 的 reason 列）

| reason | 含义 / 处理 |
|---|---|
| `no_access` | 无机构权限（机构没订这篇）→ 馆际互借 / NSTL |
| `elsevier_preview` | Elsevier 只返回首页预览（无 insttoken 或被**限流**）→ 见下方排障 |
| `no_pdf` | 没找到 PDF 直链 |
| `blocked` | 拿到的不是 PDF（疑似反爬/会话未建好）→ 重试一次往往就好 |
| `timeout` | 页面或下载超时（自动重试 2 次） |
| `no_adapter` | 该 DOI 前缀还没适配 |
| `metadata_error` | Crossref 解析该 DOI 失败 |

更多排障（代理坑 / 限流冷却 / 短信绑定 / Shibboleth 偶发卡 IdP / Xvfb）见 `skill/references/troubleshooting.md`。

> **关于 Elsevier 限流**：短时间反复下同一篇会触发 ScienceDirect 风控、返回空壳预览页（`elsevier_preview`）。保持默认限速、别反复重试，停手几十分钟到几小时会自动恢复。

---

## 安全与合规

- 凭证只存本地 `.paperdl.env`（`chmod 600`），登录态存 `.profile/`，均 gitignore，不上传。
- **限速 8–20 秒/篇、单次有上限**，避免触发出版商风控、连累机构 IP。
- 只走机构合规渠道，**不做 Sci-Hub 之类第三方源**。

---

## 做成 Skill / Codex 包（分享给同事）

把整套脱敏打包成一个自包含目录，同事在 **Claude Code 或 Codex** 里都能用：

```bash
python scripts/make_skill.py ~/.claude/skills/paperdl
```

产物含 `SKILL.md`（Claude Code 入口）、`AGENTS.md`（Codex 入口）、脱敏后的源码 `app/`、`references/`（排障 + `.paperdl.env` 模板）。打包用白名单机制，**绝不带任何人的 `.paperdl.env` / `.profile` / 下载文件 / 账号库**。每个人拿到后用 `paperdl config` 配自己的账号。

---

## 开发

```bash
/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest -q   # 跑测试
```

设计与实施文档见 `docs/superpowers/`。代码结构：`paperdl/`（cli / session / shibboleth / downloader / adapters / web / configure / doctor），`paperdl/search/`（检索：base / openalex / export），`scripts/`（setup.sh / make_skill.py），`skill/`（SKILL.md / AGENTS.md / references）。
