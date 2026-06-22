#!/usr/bin/env bash
# 构建 paperdl 镜像。为了不依赖国际网络(cdn.playwright.dev)，把宿主已下好的 patchright
# Chromium 暂存进 build 上下文(.docker/)，Dockerfile 直接 COPY 进镜像。
#
# 前提：宿主已 `patchright install chromium`（本仓库开发环境已具备）。
# 没有缓存时，可改 Dockerfile 那行为 `RUN patchright install chromium`（需 build 网络能直连 CDN）。
set -euo pipefail
cd "$(dirname "$0")/.."

CACHE="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
CHROMIUM_DIR=$(ls -d "$CACHE"/chromium-* 2>/dev/null | grep -v headless_shell | sort | tail -1 || true)
if [ -z "$CHROMIUM_DIR" ]; then
  echo "❌ 没找到 patchright Chromium 缓存（$CACHE/chromium-*）。先在宿主跑：patchright install chromium" >&2
  exit 1
fi

echo "暂存 Chromium 进 build 上下文：$CHROMIUM_DIR"
rm -rf .docker && mkdir -p .docker/ms-playwright
cp -r "$CHROMIUM_DIR" .docker/ms-playwright/

echo "docker build -t paperdl:latest ..."
docker build -t paperdl:latest .

echo "清理暂存"
rm -rf .docker
echo "✅ 镜像 paperdl:latest 就绪。分享给同事：docker save paperdl:latest | gzip > paperdl.tar.gz"
