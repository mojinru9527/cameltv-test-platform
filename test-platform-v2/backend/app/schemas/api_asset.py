"""接口测试模块 Pydantic schemas — 服务、接口资产、导入、任务。"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


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
    request_schema: str = "{}"
    response_schema: str = "{}"
    auth_required: bool = False


class ApiEndpointUpdate(BaseModel):
    module: str | None = None
    summary: str | None = None
    description: str | None = None
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

class ApiTaskCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    environment_id: int | None = None
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
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApiTaskDetailOut(ApiTaskOut):
    items: list[ApiTaskItemOut] = []


# ── Case Generation ──

class GenerateApiCasesRequest(BaseModel):
    endpoint_id: int | None = None
    endpoint_data: dict | None = None  # 手动传入的接口定义（不依赖已保存的 endpoint）
    templates: list[str] = Field(default=["basic", "boundary", "invalid", "idempotency"])
    import_to_case_library: bool = True
    module: str = ""
    service_name: str = ""


class BatchGenerateRequest(BaseModel):
    endpoint_ids: list[int] = Field(..., min_length=1, max_length=100)
    templates: list[str] = Field(default=["basic", "boundary", "invalid", "idempotency"])
    import_to_case_library: bool = True
