"""接口测试模块 Pydantic schemas — 服务、接口资产、导入、任务。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator


# ── ApiService ──

class ApiServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = ""
    description: str = ""
    default_base_path: str = ""
    owner: str = ""


class ApiServiceUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    default_base_path: str | None = None
    owner: str | None = None
    status: str | None = None


class ApiServiceOut(BaseModel):
    id: int
    project_id: int
    name: str
    display_name: str
    description: str
    default_base_path: str
    owner: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── ApiEndpoint ──

class ApiEndpointCreate(BaseModel):
    service_id: int
    module: str = ""
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    path: str = Field(..., min_length=1)
    summary: str = ""
    description: str = ""
    remark: str = ""
    request_schema: str = "{}"
    response_schema: str = "{}"
    auth_required: bool = False


class ApiEndpointUpdate(BaseModel):
    service_id: int | None = None
    module: str | None = None
    summary: str | None = None
    description: str | None = None
    remark: str | None = None
    request_schema: str | None = None
    response_schema: str | None = None
    auth_required: bool | None = None
    deprecated: bool | None = None
    version: str | None = None


class ApiEndpointOut(BaseModel):
    id: int
    project_id: int
    service_id: int
    module: str
    method: str
    path: str
    summary: str
    description: str
    remark: str
    request_schema: str
    response_schema: str
    auth_required: bool
    deprecated: bool
    source: str
    import_batch_id: int | None
    version: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── OpenAPI Import ──

class OpenApiImportPreviewRequest(BaseModel):
    service_name: str = Field(..., min_length=1)
    source_type: str = Field(default="openapi_url")  # openapi_url | openapi_file | openapi_text
    source_ref: str = ""  # URL or filename
    spec_content: str | None = None  # inline spec content (for text import)


class OpenApiImportConfirmRequest(BaseModel):
    service_name: str = Field(..., min_length=1)
    source_type: str = "openapi_url"
    source_ref: str = ""
    spec_content: str | None = None
    generate_cases: bool = False  # 导入后是否批量生成用例
    create_plan: bool = False    # 导入后是否自动创建测试计划
    plan_name: str = ""          # 自动创建计划的名称（为空则自动生成）


class ApiImportPreviewOut(BaseModel):
    service_name: str
    version: str
    total_count: int
    new_count: int
    existing_count: int
    endpoints: list[dict]
    errors: list[dict] = []


class ApiImportResultOut(BaseModel):
    batch_id: int
    service_name: str
    version: str
    total_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    generated_case_count: int = 0
    errors: list[dict] = []


# ── API Execution Task ──

class ApiRequestDefinition(BaseModel):
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    url: str = Field(..., min_length=1)
    headers: dict[str, Any] = Field(default_factory=dict)
    body: str = ""
    query_params: dict[str, Any] = Field(default_factory=dict)
    assertions: list[dict[str, Any]] = Field(default_factory=list)


class ApiExecutionRequest(BaseModel):
    """Shared request contract for all API execution entry points.

    The pre-validator keeps the former flat quick-execute payload readable while
    new callers use the nested request definition consistently.
    """

    source: Literal["quick", "asset", "single", "group", "batch"] = "single"
    environment_id: int | None = None
    dataset_id: int | None = None
    case_ids: list[int] = Field(default_factory=list, max_length=500)
    request: ApiRequestDefinition | None = None
    confirm_prod: bool = False

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_quick_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict) or "request" in value or "url" not in value:
            return value

        def parse_json(raw: Any, default: Any) -> Any:
            if not isinstance(raw, str):
                return raw if raw is not None else default
            try:
                return json.loads(raw) if raw.strip() else default
            except json.JSONDecodeError:
                return default

        normalized = dict(value)
        normalized["source"] = normalized.get("source") or "quick"
        normalized["request"] = {
            "method": normalized.pop("method", "GET"),
            "url": normalized.pop("url"),
            "headers": parse_json(normalized.pop("headers", {}), {}),
            "body": normalized.pop("body", ""),
            "query_params": parse_json(normalized.pop("query_params", {}), {}),
            "assertions": parse_json(normalized.pop("assertions", []), []),
        }
        normalized.pop("service_name", None)
        return normalized


class ApiTaskCreateRequest(ApiExecutionRequest):
    source: Literal["group", "batch"] = "batch"
    name: str = Field(..., min_length=1)
    service_id: int | None = None
    case_ids: list[int] = Field(..., min_length=1, max_length=500)


class ApiTaskOut(BaseModel):
    id: int
    project_id: int
    task_id: str
    name: str
    environment_id: int | None
    service_id: int | None
    status: str
    total: int
    passed: int
    failed: int
    skipped: int
    trigger_type: str
    creator_id: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    cancel_requested: bool = False
    confirm_prod: bool = False
    retry_count: int = 0
    max_retries: int = 1
    locked_at: datetime | None = None
    locked_by: str = ""
    timeout_seconds: int = 1800

    model_config = {"from_attributes": True}


class ApiTaskItemOut(BaseModel):
    id: int
    task_id: int
    case_id: int
    status: str
    duration_ms: float
    request_snapshot: str
    response_snapshot: str
    assertion_results: str
    error_message: str
    error_type: str = ""
    test_execution_id: int | None = None  # Batch 157：关联计划执行记录
    retry_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def curl_command(self) -> str:
        """从 request_snapshot 中提取 curl 命令。"""
        try:
            snap = json.loads(self.request_snapshot) if self.request_snapshot else {}
        except (json.JSONDecodeError, TypeError):
            return ""
        return snap.get("curl", "") or ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def truncated(self) -> bool:
        """从 response_snapshot 中提取 truncated 标记。"""
        try:
            snap = json.loads(self.response_snapshot) if self.response_snapshot else {}
        except (json.JSONDecodeError, TypeError):
            return False
        return snap.get("truncated", False)


class ApiTaskDetailOut(ApiTaskOut):
    items: list[ApiTaskItemOut] = []


# ── Case Generation ──

class GenerateApiCasesRequest(BaseModel):
    endpoint_id: int | None = None
    endpoint_data: dict | None = None  # 手动传入的接口定义（不依赖已保存的 endpoint）
    templates: list[str] = Field(default=[
        "basic", "boundary", "invalid", "security", "idempotency", "extreme",
        "smoke", "scenario", "extra_param", "security_ext", "performance_low",
        "data_test", "stability", "compatibility", "monitoring",
    ])
    import_to_case_library: bool = True
    module: str = ""
    service_name: str = ""


class BatchGenerateRequest(BaseModel):
    endpoint_ids: list[int] = Field(..., min_length=1, max_length=100)
    templates: list[str] = Field(default=[
        "basic", "boundary", "invalid", "security", "idempotency", "extreme",
        "smoke", "scenario", "extra_param", "security_ext", "performance_low",
        "data_test", "stability", "compatibility", "monitoring",
    ])
    import_to_case_library: bool = True
