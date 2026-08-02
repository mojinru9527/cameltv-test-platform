# ── Builder stage ──
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS builder
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY test-platform-v2/backend/requirements.txt test-platform-v2/backend/requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

# ── Runtime stage ──
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
ARG APP_UID=10001
ARG APP_GID=10001
WORKDIR /app

# Keep Python dependencies outside root's home so the runtime user can import
# them without widening permissions on /root.
COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    WORKSPACE_ROOT=/app \
    LANHU_MCP_DIR=/app/lanhu-mcp \
    DATA_DIR=/data/lanhu \
    HOME=/home/cameltv \
    XDG_CACHE_HOME=/home/cameltv/.cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        ffmpeg \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" cameltv \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --home-dir /home/cameltv --shell /usr/sbin/nologin cameltv

# Install the npm-locked UI runner before copying specs so source edits retain
# the dependency/browser cache layer. Align Python Playwright to the same
# release so Lanhu screenshots and UI jobs share one Chromium installation.
COPY test-platform-v2/backend/tests/playwright/package*.json ./tests/playwright/
RUN PLAYWRIGHT_VERSION="$(node -p "require('./tests/playwright/package-lock.json').packages['node_modules/playwright'].version")" \
    && pip install --no-cache-dir --no-deps --force-reinstall "playwright==${PLAYWRIGHT_VERSION}" \
    && cd /app/tests/playwright \
    && npm ci \
    && ./node_modules/.bin/playwright install --with-deps chromium \
    && python -m playwright install chromium \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*

COPY test-platform-v2/backend/app ./app
COPY test-platform-v2/backend/alembic ./alembic
COPY test-platform-v2/backend/alembic.ini .
COPY test-platform-v2/backend/tests/playwright ./tests/playwright

# lanhu-mcp 是 Git 子模块，云构建（Railway/Vercel/CI）默认不拉取子模块内容。
# 这里在构建期直接从子模块 remote 拉取，保证无本地子模块也能构建。
RUN git clone --depth 1 --branch main \
        https://github.com/mojinru9527/lanhu-mcp.git /tmp/lanhu-mcp \
    && mkdir -p /app/lanhu-mcp \
    && cp /tmp/lanhu-mcp/lanhu_mcp_server.py /app/lanhu-mcp/lanhu_mcp_server.py \
    && rm -rf /tmp/lanhu-mcp

RUN mkdir -p /app/storage /data/lanhu /ms-playwright "${XDG_CACHE_HOME}" \
    && chown -R cameltv:cameltv /app /data /ms-playwright /home/cameltv

USER cameltv:cameltv
EXPOSE 8000
CMD ["sh", "-c", "echo '=== CamelTv Test Platform v2.6 ===' && test \"$(alembic heads | grep -c ' (head)$')\" -eq 1 && echo 'Running database migrations...' && alembic upgrade head && echo 'Starting application...' && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
