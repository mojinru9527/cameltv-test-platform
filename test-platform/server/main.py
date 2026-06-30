"""FastAPI 主入口 — CamelTv 测试平台 REST API。

启动: uvicorn server.main:app --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routes import (
    config, envcheck, api_test, ui_auto, datafactory,
    report, task_history, test_cases, test_plans, workspace,
)

app = FastAPI(
    title="CamelTv 测试平台 API",
    version="0.3.0",
    description="可移植测试自动化平台 — REST API",
)

# CORS：从环境变量 ALLOWED_ORIGINS 读取（逗号分隔）。
# 未设置时默认仅放行本地前端开发端口，避免 Docker 部署后 0.0.0.0:8000 被任意站点跨域调用。
_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _origins_env == "*":
    allow_origins = ["*"]
elif _origins_env:
    allow_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
else:
    allow_origins = ["http://localhost", "http://localhost:80",
                     "http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 (v0.3.0)
app.include_router(config.router, prefix="/api")
app.include_router(envcheck.router, prefix="/api")
app.include_router(api_test.router, prefix="/api")
app.include_router(ui_auto.router, prefix="/api")
app.include_router(datafactory.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(task_history.router, prefix="/api")
app.include_router(test_cases.router, prefix="/api")
app.include_router(test_plans.router, prefix="/api")
app.include_router(workspace.router, prefix="/api")


@app.get("/")
def root():
    return {"service": "CamelTv Test Platform API", "version": "0.2.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
