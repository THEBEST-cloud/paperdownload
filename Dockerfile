# paperdl 容器镜像。容器内永远是 Linux，靠内置 Xvfb 跑有头 patchright Chromium 过 Cloudflare，
# 所以 macOS/Windows 用户只要装 Docker Desktop 即可，无需任何系统适配。
#
# 持久化数据用 volume 挂载：.paperdl.env(凭证)、.profile(登录态)、downloads(产物)、web_data(网页任务)。
# 首次需在容器内做一次性登录(含短信绑定)：
#   docker run -it --rm -v $PWD/data/.paperdl.env:/app/.paperdl.env \
#       -v $PWD/data/.profile:/app/.profile paperdl login
FROM python:3.11-slim

# Xvfb + Chromium 运行所需的系统库；poppler-utils 提供 pdfinfo(Elsevier 预览检测用)
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb ca-certificates fonts-liberation poppler-utils \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 libxshmfence1 libx11-6 \
    libxcb1 libxext6 libxi6 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY paperdl ./paperdl
# 装包(走清华 PyPI 镜像，国内网络稳)
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -e .
# 把宿主已下好的 patchright Chromium 烤进镜像(免国际 CDN 下载，确定性 build)。
# 若你的 build 网络能直连 cdn.playwright.dev，也可改成： RUN patchright install chromium
COPY .docker/ms-playwright /root/.cache/ms-playwright

COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8200
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8200"]
