"""接口测试资产模型 — API 服务、接口端点、导入批次、执行任务、任务明细。"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ApiService(Base, TimestampMixin):
    """项目下的后端服务分组，例如 account-service、camel-service。"""
    __tablename__ = "api_service"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_api_service_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(index=True)
    display_name: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(default="")
    default_base_path: Mapped[str] = mapped_column(default="")
    owner: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="active")


class ApiImportBatch(Base, TimestampMixin):
    """OpenAPI/Swagger 导入批次记录。"""
    __tablename__ = "api_import_batch"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    service_id: Mapped[int] = mapped_column(index=True)
    source_type: Mapped[str] = mapped_column(default="openapi")
    source_ref: Mapped[str] = mapped_column(default="")
    version: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="pending")
    total_count: Mapped[int] = mapped_column(default=0)
    created_count: Mapped[int] = mapped_column(default=0)
    updated_count: Mapped[int] = mapped_column(default=0)
    skipped_count: Mapped[int] = mapped_column(default=0)
    error_detail: Mapped[str] = mapped_column(Text, default="")


class ApiEndpoint(Base, TimestampMixin):
    """接口资产 — 从 OpenAPI 导入或手动创建的接口定义。"""
    __tablename__ = "api_endpoint"
    __table_args__ = (UniqueConstraint("project_id", "service_id", "method", "path", name="uq_api_endpoint_identity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    service_id: Mapped[int] = mapped_column(index=True)
    module: Mapped[str] = mapped_column(default="", index=True)
    method: Mapped[str] = mapped_column(default="GET", index=True)
    path: Mapped[str] = mapped_column(default="", index=True)
    summary: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(Text, default="")
    request_schema: Mapped[str] = mapped_column(Text, default="{}")
    response_schema: Mapped[str] = mapped_column(Text, default="{}")
    auth_required: Mapped[bool] = mapped_column(default=False)
    deprecated: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(default="manual")
    import_batch_id: Mapped[int | None] = mapped_column(default=None, index=True)
    version: Mapped[str] = mapped_column(default="")


class ApiExecutionTask(Base, TimestampMixin):
    """批量执行任务 — 从用例列表多选发起的执行任务。"""
    __tablename__ = "api_execution_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    task_id: Mapped[str] = mapped_column(default="", index=True)
    name: Mapped[str] = mapped_column(default="")
    environment_id: Mapped[int | None] = mapped_column(default=None, index=True)
    service_id: Mapped[int | None] = mapped_column(default=None, index=True)
    status: Mapped[str] = mapped_column(default="pending", index=True)
    total: Mapped[int] = mapped_column(default=0)
    passed: Mapped[int] = mapped_column(default=0)
    failed: Mapped[int] = mapped_column(default=0)
    skipped: Mapped[int] = mapped_column(default=0)
    trigger_type: Mapped[str] = mapped_column(default="manual")
    creator_id: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class ApiExecutionTaskItem(Base, TimestampMixin):
    """批量执行任务明细 — 每条用例的执行结果快照。"""
    __tablename__ = "api_execution_task_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(index=True)
    case_id: Mapped[int] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default="pending", index=True)
    duration_ms: Mapped[float] = mapped_column(default=0)
    request_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    response_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    assertion_results: Mapped[str] = mapped_column(Text, default="[]")
    error_message: Mapped[str] = mapped_column(Text, default="")
