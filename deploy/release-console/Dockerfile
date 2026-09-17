# release-console — 独立发布控制台（与测试平台解耦）
# 仅含 FastAPI + uvicorn + openssh-client（执行器 SSH 依赖），镜像极小。
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# C249-7：改为通配拷贝——显式列举会在新增模块时漏拷（Batch 249 的 `migrations.py`
# 一度没进镜像，控制面会 import 失败起不来，属"恢复平面"自锁）。守护测试见
# tests/test_dockerfile_copy_guard.py（按 import 图校验覆盖）。
COPY *.py ./
COPY static ./static

EXPOSE 8003
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
