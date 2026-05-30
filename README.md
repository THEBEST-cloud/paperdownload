# paperdl

按 DOI 清单批量下载文献的命令行工具（阶段 0：框架 + Springer）。

通过中科院文献情报中心（las.ac.cn / 中国科技云通行证）的机构权限下载。**不存账号密码**——登录是你在脚本弹出的浏览器里手动完成的，会话保存在本地 `.profile/`。

## 安装

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## 用法

**第一步：登录（每隔几天会话过期后重做一次）**

```bash
python -m paperdl login
```

弹出浏览器后：
1. 用中国科技云通行证登录（账号=中科院邮箱），处理验证码/二次验证；
2. 点进 Springer（link.springer.com）做一次机构登录，确认能看到全文；
3. 回终端按回车保存会话。

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
| `no_adapter` | 该出版商阶段 0 还没适配（目前仅 Springer） |
| `no_access` | 没解析到下载链接/疑似无机构权限或被要求重新登录 |
| `no_pdf` | 文章页里没找到 PDF 下载链接 |
| `blocked` | 拿到的不是 PDF（疑似反爬拦截） |
| `timeout` | 页面或下载超时（会自动重试 2 次） |
| `metadata_error` | Crossref 解析该 DOI 失败 |

## 现状

- ✅ 已实现并测试：框架、Crossref 解析、限速/重试/去重、Springer 适配。
- ⏳ 待你手动验证：Springer 真实端到端下载（需你登录 + 一个有权限的真实 Springer DOI）。
- 🔜 后续阶段：Elsevier、Wiley/Nature、ACS/RSC/IEEE/IOP/APS、国内库 CNKI/万方/维普。

设计与计划见 `docs/superpowers/`。
