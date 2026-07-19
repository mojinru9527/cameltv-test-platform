"""测试用例 Schema — 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── 响应 ──────────────────────────────────────────────

class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    case_id: str = ""
    title: str = ""
    domain: str = ""
    module: str = ""
    case_type: str = "manual"
    priority: str = "P2"
    status: str = "active"
    tags: str = "[]"
    preconditions: str = ""
    steps: str = "[]"
    expected_result: str = ""
    api_method: str = ""
    api_endpoint: str = ""
    api_spec_ref: str = ""
    api_headers: str = "{}"
    api_body: str = ""
    api_assertions: str = "[]"
    source: str = "migration"
    source_doc_id: Optional[int] = None
    old_id: Optional[int] = None
    review_status: str = "draft"
    review_comment: str = ""
    reviewer_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TestCaseBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_id: str = ""
    title: str = ""
    domain: str = ""
    module: str = ""
    case_type: str = "manual"
    priority: str = "P2"


# ── 请求 ──────────────────────────────────────────────

class TestCaseCreate(BaseModel):
    project_id: int = 0
    case_id: str = ""
    title: str
    domain: str = ""
    module: str = ""
    case_type: str = "manual"
    priority: str = "P2"
    status: str = "active"
    tags: str = "[]"
    preconditions: str = ""
    steps: str = "[]"
    expected_result: str = ""
    api_method: str = ""
    api_endpoint: str = ""
    api_spec_ref: str = ""
    api_headers: str = "{}"
    api_body: str = ""
    api_assertions: str = "[]"
    source: str = "manual"


class TestCaseUpdate(BaseModel):
    case_id: Optional[str] = None
    title: Optional[str] = None
    domain: Optional[str] = None
    module: Optional[str] = None
    case_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[str] = None
    expected_result: Optional[str] = None
    api_method: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_spec_ref: Optional[str] = None
    api_headers: Optional[str] = None
    api_body: Optional[str] = None
    api_assertions: Optional[str] = None


# ── 查询参数 ──────────────────────────────────────────

class TestCaseFilter(BaseModel):
    domain: str = ""
    module: str = ""
    case_type: str = ""           # 空=全部
    priority: str = ""
    status: str = ""
    keyword: str = ""
    page: int = 1
    page_size: int = 20


# ── 域树 ──────────────────────────────────────────────

class ModuleNode(BaseModel):
    module: str
    count: int = 0


class DomainNode(BaseModel):
    domain: str
    count: int = 0
    modules: list[ModuleNode] = []


# ── 分类管理 ──────────────────────────────────────────

class CategoryCreate(BaseModel):
    project_id: int = 0
    name: str


class CategoryUpdate(BaseModel):
    name: str | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int = 0
    name: str
    is_deleted: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DomainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int = 0
    name: str
    is_deleted: bool = False
    modules: list["ModuleOut"] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int = 0
    domain_id: int
    name: str
    is_deleted: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ModuleCreate(BaseModel):
    domain_id: int
    name: str
