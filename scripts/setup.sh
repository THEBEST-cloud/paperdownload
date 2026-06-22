#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

echo "[1/4] 建虚拟环境 .venv ..."
[ -d .venv ] || "$PY" -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate

echo "[2/4] 安装 paperdl 及依赖 ..."
pip install -q -U pip
pip install -q -e .

echo "[3/4] 安装 patchright chromium ..."
patchright install chromium

echo "[4/4] 检查 Xvfb ..."
if command -v Xvfb >/dev/null 2>&1; then
  echo "  Xvfb OK"
else
  echo "  ⚠️ 未装 Xvfb：sudo apt-get install -y xvfb"
fi

echo
echo "完成。下一步：.venv/bin/paperdl config   然后   .venv/bin/paperdl login"
