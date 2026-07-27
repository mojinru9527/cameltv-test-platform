"""API 请求/响应 Pydantic 模型。"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    project: str
    version: str
    environments: list[str]
    current_env: str = ""
    base_url: str = ""
    proxy_strategy: str = ""


class EnvCheckRequest(BaseModel):
    env: str = "test"


class EnvCheckResponse(BaseModel):
    env: str
    status: str  # ok | warn | fail
    checks: list[dict[str, Any]]
    total: int
    passed: int
    failed: int
    warnings: int


class ApiTestRequest(BaseModel):
    env: str = "test"
    filter: str = ""  # smoke | regression | ""


class ApiTestResponse(BaseModel):
    run_id: str
    env: str
    status: str
    total: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    failed_cases: list[dict[str, Any]]


class DataFactoryRequest(BaseModel):
    env: str = "test"
    rule: str = ""       # 数据规则 YAML 路径
    template: str = ""   # 模板名
    count: int = 10


class TaskHistoryItem(BaseModel):
    id: int
    task_type: str
    env: str
    status: str
    started_at: str
    finished_at: str = ""
    result_summary: str = ""


class ReportSummary(BaseModel):
    run_id: int
    build: str
    source: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    ts: str = ""
