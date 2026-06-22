# paperdl 排障手册

## 代理坑

环境变量 `http_proxy` / `https_proxy` / `all_proxy` 会让 patchright 浏览器走境外出口。中科院通行证（CSTCloud）检测到陌生境外 IP 时会视为可疑设备，导致短信验证码无法正常触发、机构 Shibboleth 权限无法识别，最终登录失败或鉴权失败。

**解决方法：** 跑 paperdl 前先 `unset http_proxy https_proxy all_proxy`；也可将 paperdl 加入代理排除列表。`paperdl doctor` 会自动检测代理环境变量并给出警告。

---

## 一次性短信绑定

首次在新设备（或新 .profile 目录）执行 `paperdl login` 时，CSTCloud 通行证会识别陌生设备，要求绑定手机号并发送短信验证码完成二次认证。绑定成功后，浏览器 .profile（保存在本机 `.profile/` 目录）会被标记为受信任设备，有效期约 10 天，期间无需重复短信验证。

**注意：** `.profile/` 目录含会话凭证，不要上传代码仓库或与他人共享。

---

## Elsevier / ScienceDirect 限流

短时间内反复请求同一篇或大量 Elsevier 文章时，会触发 ScienceDirect 风控，返回空壳 HTML 页（adapter 内称 `elsevier_preview`，无实际 PDF 内容）。此时继续重试只会加剧封锁。

**解决方法：** 保持默认限速（每篇间隔 8–20 秒），不要在短时间内手动反复重试同一批文章。触发限流后等待几十分钟到几小时，限流会自动解除。`paperdl retry` 会重试所有之前失败的条目，适合限流解除后补跑。

---

## 被打断后续跑

下载任务中途被中断（网络断开、手动 Ctrl+C、机器重启等）时，已下载的文章不会丢失，状态写在 `results.csv` 中。

- **网页端（`paperdl serve`）：** 打开任务页面，点击「继续下载」按钮即可补跑所有 pending 条目。
- **CLI：** 执行 `paperdl retry`，自动重试所有状态为 failed 的条目；pending 条目可通过重新 `paperdl run <清单.txt>` 跳过已完成条目继续。

---

## Shibboleth 偶发卡 IdP

ACS（美国化学学会）、Atypon 平台等出版商走机构 Shibboleth SSO 时，偶尔会卡在 Identity Provider（IdP）跳转页，页面长时间无响应。paperdl 内部已对此场景内置重建会话后重试逻辑。

如果重建后仍失败，手动对该 DOI 单独重试（网页端单条重试按钮，或 `paperdl retry`）通常可以恢复。若某个出版商持续失败，可先跳过，等待一段时间后再试。

---

## xvfb / 有头浏览器

paperdl 使用 patchright（stealth Chromium）绕过 Cloudflare Bot 检测，必须有图形显示环境。在无显示器的服务器上运行时，需要 Xvfb 提供虚拟帧缓冲。

`paperdl doctor` 会检测当前环境是否有可用的显示（`DISPLAY` 变量 / Xvfb），并在缺失时给出警告。

**解决方法：**
```bash
sudo apt-get install -y xvfb
Xvfb :99 -screen 0 1280x800x24 &
export DISPLAY=:99
paperdl run dois.txt
```
或使用 `xvfb-run` 包装：
```bash
xvfb-run --auto-servernum paperdl run dois.txt
```
