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
    DATA_DIR=/app/storage/lanhu-data \
    HOME=/home/cameltv \
    XDG_CACHE_HOME=/home/cameltv/.cache

# Node 22（NodeSource）：dsh CLI 依赖 commander>=22.12 / pi-ai>=22.19，
# Debian apt 的 nodejs（18/20）不满足（Batch 191 生产构建报 EBADENGINE）。
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        ffmpeg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
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

# lanhu-mcp 是 Git 子模块。优先使用构建上下文中的本地子模块文件
# （自建服务器/离线构建场景）；缺失时从 remote 拉取（云构建场景）。
# 注意：不能以 "COPY lanhu-mcp/..." 探测子模块是否本地存在——COPY 源缺失时
# 构建会直接失败，RUN 里的回退分支根本不会执行（#300 生产部署回调）。
# 改用 BuildKit bind-mount：把上下文中的 lanhu-mcp 目录挂进构建环境，
# 本地构建（子模块已初始化、文件存在）直接复制；云构建（Railway/CI 的
# checkout 中子模块为未初始化空目录）走 git clone 回退。
RUN --mount=type=bind,source=lanhu-mcp,target=/lanhu-mcp-src \
    if [ -s /lanhu-mcp-src/lanhu_mcp_server.py ]; then \
      mkdir -p /app/lanhu-mcp \
      && cp /lanhu-mcp-src/lanhu_mcp_server.py /app/lanhu-mcp/lanhu_mcp_server.py; \
    else \
      git clone --depth 1 --branch main https://github.com/mojinru9527/lanhu-mcp.git /tmp/lanhu-mcp \
      && mkdir -p /app/lanhu-mcp \
      && cp /tmp/lanhu-mcp/lanhu_mcp_server.py /app/lanhu-mcp/lanhu_mcp_server.py \
      && rm -rf /tmp/lanhu-mcp; \
    fi

# ── DSH 运行时（Batch 191 生产启用）──────────────────────────────
# npm 发布版 @deepseek-ai/dsh 依赖自洽（dsh-base/dsh-headless 随依赖树安装，
# 容器模拟已验证：npm 全局 dsh 0.1.0-rc.7 + pnpm 11 + agent-team profile
# dump-config 组合自检通过）；agent-team profile 供团队模式使用。
# CLI 方式 A（dsh plugin add）生成的 bundles 缺 @deepseek-ai/dsh-headless →
# 任务挂起（见 agent-team/README.md），构建期用 node 补丁补齐后再自检。
# pnpm 为 dsh plugin 命令所需（转发 pnpm 安装插件）；必须用 pnpm 11+
# （pnpm 9 对 workspace root 的 add 报 ERR_PNPM_ADDING_TO_ROOT）。
# 生产 DSH_HARNESS_PATH=/usr/local/lib/node_modules/@deepseek-ai/dsh/lib/bin.js
# （NodeSource Node 22 布局实际为 /usr/lib/node_modules/...，生产环境变量按此配置）
RUN npm install -g pnpm@11 \
    && npm install -g @deepseek-ai/dsh@0.1.0-rc.7 \
    && DSH_HOME=/home/cameltv/.dsh dsh plugin --profile agent-team add '@nanmicoder/dsh-agent-teams@^0.1.5' \
    && node -e "const fs=require('fs');const p='/home/cameltv/.dsh/profiles/agent-team/package.json';const j=JSON.parse(fs.readFileSync(p));if(!j.dsh.profile.bundles.includes('@deepseek-ai/dsh-headless')){j.dsh.profile.bundles.splice(1,0,'@deepseek-ai/dsh-headless');fs.writeFileSync(p,JSON.stringify(j,null,2));console.log('agent-team bundles:',j.dsh.profile.bundles.join(','))}" \
    # Batch 191 船长纪律（生产实测补强）：覆盖写用户 patch 层，禁用 generic
    # subagent 派活工具——船长必须用 agent_teams_* 九件套自组织团队（与本地
    # $DSH_HOME 配置一致；缺失时模型混用 subagent 工具导致成员任务挂起/收尾过早）
    && printf '%s\n' \
        '# 禁用 generic subagent 派活工具（Batch 191 船长纪律，见 agent-team/README.md）' \
        '- id: tool-subagent' \
        '  disabled: true' \
        '- id: tool-subagent-fork' \
        '  disabled: true' \
        '- id: tool-subagent-control' \
        '  disabled: true' \
        '- id: tool-subagent-list-agents' \
        '  disabled: true' \
        > /home/cameltv/.dsh/profiles/agent-team/cordis.patch.yml \
    && DSH_HOME=/home/cameltv/.dsh dsh --profile agent-team --dump-config >/dev/null \
    && chown -R cameltv:cameltv /home/cameltv/.dsh

RUN mkdir -p /app/storage /app/storage/lanhu-data /ms-playwright "${XDG_CACHE_HOME}" \
    && chown -R cameltv:cameltv /app /ms-playwright /home/cameltv

USER cameltv:cameltv
EXPOSE 8000
CMD ["sh", "-c", "echo '=== CamelTv Test Platform v2.6 ===' && test \"$(alembic heads | grep -c ' (head)$')\" -eq 1 && echo 'Running database migrations...' && alembic upgrade head && echo 'Starting application...' && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
