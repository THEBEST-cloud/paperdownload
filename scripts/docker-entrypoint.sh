#!/usr/bin/env bash
# 容器入口：清理上次容器残留的 Chromium 单例锁(否则换容器/重启会 ProcessSingleton 报错)，
# 然后把参数交给 paperdl。Xvfb 由 paperdl 自身按需启动(browser_context → ensure_display)。
# 凭证/登录态/产物都落在工作目录($PWD，compose 里设为挂载的 /data)。
set -e
rm -f "$PWD"/.profile/Singleton* 2>/dev/null || true
exec paperdl "$@"
