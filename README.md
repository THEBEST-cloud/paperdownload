# paperdl

按 DOI 清单批量下载文献的命令行工具。

通过中科院文献情报中心（las.ac.cn / 中国科技云通行证）的机构权限下载。账号密码只存在本地 gitignore 的 `.paperdl.env`，不上传、不进代码库。

**已支持**：Springer、Nature、RSC（浏览器 + 机构 IP）、Elsevier、Wiley（官方 API/TDM，绕开 Cloudflare）。

**两种取全文机制**：
- 浏览器型（Springer 等）：直连中科院网络 IP，出版商按机构 IP 放行全文。
- API 型（Elsevier）：用官方 API key + 机构 IP，绕开 ScienceDirect 的 Cloudflare/Shibboleth 墙。

## 安装

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## 用法

**第一步（只做一次）：填账号密码**

```bash
cp .paperdl.env.example .paperdl.env
# 编辑 .paperdl.env，填入你的中国科技云通行证账号(中科院邮箱)和密码
```

`.paperdl.env` 已被 git 忽略，只存在你本地，不上传、不进代码库。也可以改用环境变量 `CSTCLOUD_ID` / `CSTCLOUD_PASSWORD`（优先级高于文件）。

下 Elsevier 文献还需在 `.paperdl.env` 填一个免费的 Elsevier API key（在 https://dev.elsevier.com 申请）：`ELSEVIER_API_KEY=...`。全文权限靠机构 IP；若仅 key 取不到全文，再向图书馆要机构令牌填 `ELSEVIER_INSTTOKEN=`。

**第二步：登录（每隔约 10 天会话过期后重做一次）**

```bash
python -m paperdl login
```

会弹出浏览器并**自动**用 `.paperdl.env` 里的账号密码登录通行证（勾选"10天保持登录"）：
- 正常情况：提示"✅ 自动登录成功"，你不用动。
- 万一弹了验证码/二次验证：提示你在浏览器里手动点一下（不会卡死）。
- 如某出版商点进去还要"机构登录"，此时在浏览器里点一次。

完成后回终端按回车保存会话。

**第二步：准备 DOI 清单**

纯文本，每行一个 DOI（也兼容 csv，取第一列、自动跳过表头）：

```
10.1007/s00339-021-04567-w
10.1007/s11431-020-1234-5
```

**第三步：下载**

```bash
python -m paperdl run mylist.txt          # 默认单次最多 50 篇，每篇间隔 8–20 秒
python -m paperdl run mylist.txt --max 10 # 自定义单次上限
python -m paperdl retry                   # 只重试上次失败的条目
```

PDF 存到 `downloads/`，每篇结果（成功/失败及原因）记到 `results.csv`。重复跑会自动跳过已成功的。

## 失败原因（results.csv 的 reason 列）

| reason | 含义 |
|---|---|
| `no_adapter` | 该出版商还没适配（目前支持 Springer、Elsevier） |
| `no_access` | 无机构权限/被要求重新登录（Elsevier 多为缺机构令牌） |
| `no_pdf` | 没找到 PDF（或 Elsevier API 只返回全文 XML 非 PDF） |
| `blocked` | 拿到的不是 PDF（疑似反爬拦截） |
| `timeout` | 页面或下载超时（会自动重试 2 次） |
| `metadata_error` | Crossref 解析该 DOI 失败 |
| `no_api_key` | 该出版商需要 API key 但 .paperdl.env 未配置 |

## 现状

- ✅ 已端到端验证：框架、Crossref 解析、限速/重试/去重、通行证自动登录（含一次性短信设备验证）、直连绕代理、**Springer / Nature / RSC**（浏览器/IP）、**Elsevier / Wiley**（官方 API/TDM）。
- ⚠️ 暂未做（反爬硬墙、无干净路径）：ACS（Cloudflare，无公开全文 API）、IOP（Radware）、APS（Cloudflare）；IEEE（Xplore 的 JS viewer，较复杂）。
- 🔜 后续：国内库 CNKI/万方/维普、NSTL 文献传递兜底。

## 出版商难度速查

| 类型 | 出版商 | 说明 |
|---|---|---|
| IP 直通（浏览器） | Springer(10.1007)、Nature(10.1038)、RSC(10.1039) | 直连机构 IP 即可，最简单 |
| 官方 API/令牌 | Elsevier(10.1016, `ELSEVIER_API_KEY`)、Wiley(10.1002/10.1111, `WILEY_TDM_TOKEN`) | 绕开反爬墙；需在 .paperdl.env 配 key/令牌 |
| 反爬硬墙（未做） | ACS(10.1021)、IOP(10.1088)、APS(10.1103) | Cloudflare/Radware，无头爬不动，无公开 API |
| 较复杂（未做） | IEEE(10.1109) | JS viewer，PDF 取得需额外工作 |

设计与计划见 `docs/superpowers/`。
