"""DSH 任务执行模块 Pydantic schemas — Batch 172 / Batch 191（团队模式）。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DshTaskCreate(BaseModel):
    """创建 DSH 任务请求。"""
    task: str = Field(..., min_length=1, max_length=20000, description="任务文本")
    params: dict = Field(default_factory=dict, description="附加参数（batch_mode 等）")
    mode: Literal["single", "team"] = "single"  # Batch 191：任务形态（默认单任务）

    @model_validator(mode="after")
    def _validate_batch_mode(self):
        """params.batch_mode 仅团队模式可用且必填（PRD US-1：批次模式必选，无默认）。"""
        batch_mode = (self.params or {}).get("batch_mode")
        if self.mode == "team":
            if batch_mode is None:
                raise ValueError("mode=team 时必须提供 params.batch_mode（full|light）")
            if batch_mode not in ("full", "light"):
                raise ValueError(f"params.batch_mode 非法: {batch_mode!r}（仅支持 full|light）")
        else:
            if batch_mode is not None:
                raise ValueError("params.batch_mode 仅团队模式（mode=team）可用")
        return self


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
    mode: str = "single"          # Batch 191：single | team
    team_json: dict = {}          # Batch 191：团队进度快照（响应恒为对象；ORM 存字符串经 before validator 转换）
    output_text: str = ""
    session_dir: str = ""
    error: str = ""
    operator_id: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("team_json", mode="before")
    @classmethod
    def _parse_team_json(cls, v):
        """ORM 字符串 → dict；损坏快照兜底为 {}（P0-1：不 500，前端显示空态）。"""
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v) if v else {}
            except json.JSONDecodeError:
                return {}
        return {}

    model_config = {"from_attributes": True}


class DshHealthOut(BaseModel):
    available: bool
    reason: str = ""
