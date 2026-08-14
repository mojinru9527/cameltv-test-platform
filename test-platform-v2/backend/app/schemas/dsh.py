"""DSH 任务执行模块 Pydantic schemas — Batch 172。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DshTaskCreate(BaseModel):
    """创建 DSH 任务请求。"""
    task: str = Field(..., min_length=1, max_length=20000, description="任务文本")
    params: dict = Field(default_factory=dict, description="附加参数（如 workspace 等）")


class DshTaskCancelResponse(BaseModel):
    id: int
    status: str
    message: str


class DshTaskOut(BaseModel):
    """DSH 任务详情/列表项。"""
    id: int
    project_id: int
    task: str
    status: str
    output_text: str = ""
    session_dir: str = ""
    error: str = ""
    operator_id: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class DshHealthOut(BaseModel):
    available: bool
    reason: str = ""
