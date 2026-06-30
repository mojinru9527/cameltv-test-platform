# API Server — Python FastAPI 后端（含 Node，供 Playwright TS 接口用例运行）
FROM python:3.12-slim

WORKDIR /app

# 系统依赖：curl（healthcheck）+ Node.js 20（Playwright 测试运行时）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 浏览器 + 系统依赖（API 测试用；此时 Node/npx 已就绪）
RUN python -m playwright install --with-deps chromium

# 应用代码
COPY core/ ./core/
COPY cli/ ./cli/
COPY tools/ ./tools/
COPY server/ ./server/
COPY config/ ./config/
COPY pyproject.toml .

# 安装 tp CLI
RUN pip install -e .

# 启动 FastAPI
EXPOSE 8000
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
