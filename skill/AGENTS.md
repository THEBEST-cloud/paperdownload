# paperdl（Codex 使用说明）

你是在用 shell 直接驱动 paperdl CLI（无需 MCP）。所有命令在本 app/ 目录下用
`.venv/bin/paperdl ...` 或激活 venv 后 `paperdl ...` 运行。先按"首次安装"配好再下载。

---

## 概述

paperdl 是一个通过中科院 CSTCloud 通行证 + las.ac.cn Shibboleth 机构订阅渠道批量下载学术论文 PDF 的命令行工具。支持 13 家主要出版商（Springer/Nature/Elsevier/ACS/Science/PNAS/Wiley/IEEE/RSC/Frontiers/AIMS Press/Annual Reviews/MDPI），并以 crossref + unpaywall 作为开放获取兜底渠道。

---

## 首次安装

```bash
# 1. 安装依赖（Python venv + patchright Chromium）
bash app/scripts/setup.sh

# 2. 配置中科院通行证账号（交互式向导，写入 .paperdl.env）
paperdl config

# 3. 自检环境（代理/Xvfb/浏览器/账号格式）
paperdl doctor

# 4. 一次性登录（首次会要求短信绑定，之后约 10 天免短信）
paperdl login
```

---

## 命令参考

| 命令 | 说明 |
|------|------|
| `paperdl config` | 交互式配置向导，填写并保存 CSTCloud 账号（及可选 API Key）到 `.paperdl.env` |
| `paperdl doctor` | 自检：检查代理环境变量、显示环境、浏览器可用性、账号配置是否完整 |
| `paperdl login` | 用配置的账号执行 CSTCloud 通行证登录，完成会话初始化（首次需短信验证） |
| `paperdl run <清单.txt>` | 批量下载：读取每行一个 DOI 的清单文件，逐篇下载 PDF |
| `paperdl retry` | 重试所有之前状态为 failed 的条目 |
| `paperdl serve --host 0.0.0.0 --port 8200` | 启动网页端（FastAPI），浏览器打开后可上传 DOI 清单、查看进度、继续下载、单条重试 |

---

## 工作流配方

### ① 新机器从零到能下

```bash
bash app/scripts/setup.sh    # 安装
paperdl config               # 填账号
paperdl doctor               # 确认环境 OK（全部 ✅ 再继续）
paperdl login                # 登录（首次短信绑定）
paperdl run dois.txt         # 开始下载
```

### ② 跑大批量清单

```bash
paperdl run dois.txt
# 如遇 Elsevier 限流（空壳页），停止后等数十分钟到数小时
paperdl retry                # 限流解除后补跑失败条目
```

### ③ 使用网页端

```bash
paperdl serve --host 0.0.0.0 --port 8200
# 浏览器打开 http://localhost:8200
# 上传 DOI 清单 → 开始下载 → 查看进度
# 任务中断后点「继续下载」补 pending 条目
# 单条失败可点「重试」
```

---

## 能力边界

**能下载：**
- 机构已订阅的期刊文章（通过 CSTCloud + Shibboleth 鉴权）
- 开放获取（OA）文章（通过 crossref/unpaywall 兜底）

**不能下载：**
- 机构未订阅的文章（下载失败时建议走 NSTL 文献传递）
- 预印本（arXiv 等）——请直接访问 arXiv.org
- 搜索功能——本工具只按 DOI 下载，不提供文献检索
- Sci-Hub 或其他非授权渠道——本工具不涉及

---

## 排障

常见问题（代理坑、短信绑定、Elsevier 限流、断点续跑、Shibboleth 卡 IdP、无头服务器 Xvfb）详见：

`references/troubleshooting.md`

---

## 安全

- 账号密码保存在本机 `.paperdl.env`（建议 `chmod 600 .paperdl.env`），不上传代码仓库
- 浏览器会话保存在本机 `.profile/` 目录，同样不应上传或共享
- `make_skill.py` 打包时白名单机制确保上述文件永不进入 skill 包
