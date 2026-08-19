"""DSH 任务执行模块 Pydantic schemas — Batch 172 / Batch 191（团队模式）。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DshTaskCreate(BaseModel):
    """创建 DSH 任务请求。"""
    task: str = Field(..., min_length=1, max_length=20000, description="任务文本")
    params: dict = Field(default_factory=dict, description="附加参数（batch_mode / team_kind 等）")
    mode: Literal["single", "team"] = "single"  # Batch 191：任务形态（默认单任务）
    scene: str = "general"                      # B1：场景标识（import_requirement/functional/api/ui/general）
    scene_params: dict = Field(default_factory=dict, description="B1：场景输入参数（需求文本/接口定义等）")

    @model_validator(mode="after")
    def _validate_batch_mode(self):
        """params.batch_mode 仅团队模式可用且必填（PRD US-1：批次模式必选，无默认）。

        DSH 测试 Agent 框架：params.team_kind 区分团队视角——dev（开发批次，默认，
        沿用 agent_team_persona）| tester（测试视角，沿用 tester_team_persona）；
        params.model 覆盖模型（模型池按任务指定，须为非空字符串）。
        """
        if self.scene not in ("import_requirement", "functional", "api", "ui", "general"):
            raise ValueError(f"scene 非法: {self.scene!r}（仅支持 import_requirement/functional/api/ui/general）")
        params = self.params or {}
        merged = dict(params)
        merged.setdefault("scene", self.scene)
        if self.scene_params:
            merged["scene_params"] = self.scene_params
        self.params = merged
        batch_mode = merged.get("batch_mode")
        team_kind = merged.get("team_kind")
        model = merged.get("model")
        if team_kind is not None and team_kind not in ("dev", "tester"):
            raise ValueError(f"params.team_kind 非法: {team_kind!r}（仅支持 dev|tester）")
        if model is not None and (not isinstance(model, str) or not model.strip()):
            raise ValueError("params.model 须为非空字符串")
        if self.mode == "team":
            if batch_mode is None:
                raise ValueError("mode=team 时必须提供 params.batch_mode（full|light）")
            if batch_mode not in ("full", "light"):
                raise ValueError(f"params.batch_mode 非法: {batch_mode!r}（仅支持 full|light）")
        else:
            if batch_mode is not None:
                raise ValueError("params.batch_mode 仅团队模式（mode=team）可用")
            if team_kind is not None:
                raise ValueError("params.team_kind 仅团队模式（mode=team）可用")
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
    scene: str = "general"        # B1：场景标识（从 params_json 提取）
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

    @field_validator("scene", mode="before")
    @classmethod
    def _scene_from_params(cls, v, info):
        """dict 构造路径下：优先从 params_json 提取 scene；无则用默认。

        from_attributes 校验走的是下方 model_validator(mode="before")——
        info.data 不含未声明字段 params_json，故 ORM 路径不依赖本 validator。
        """
        if v and v != "general":
            return v
        params = (info.data or {}).get("params_json") or "{}"
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = {}
        if isinstance(params, dict):
            return params.get("scene") or "general"
        return "general"

    @model_validator(mode="before")
    @classmethod
    def _scene_from_orm_row(cls, data):
        """from_attributes 校验时 data 是 ORM 行——从 row.params_json 提取 scene 回显。

        B1：参数提交时 scene 已合并进 params（DshTaskCreate._validate_batch_mode），
        落库 params_json；此处把 scene 解析出来作为显式字段，避免字段级 before
        validator 拿不到信息（info.data 不含未声明的 params_json）。
        """
        if isinstance(data, dict):
            return data
        if not hasattr(data, "params_json"):
            return data
        raw = getattr(data, "params_json", None) or "{}"
        scene = "general"
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict):
                scene = parsed.get("scene") or "general"
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "id": getattr(data, "id", None),
            "project_id": getattr(data, "project_id", None),
            "task": getattr(data, "task", None),
            "status": getattr(data, "status", None),
            "mode": getattr(data, "mode", None),
            "team_json": getattr(data, "team_json", "{}"),
            "scene": scene,
            "output_text": getattr(data, "output_text", ""),
            "session_dir": getattr(data, "session_dir", ""),
            "error": getattr(data, "error", ""),
            "operator_id": getattr(data, "operator_id", 0),
            "created_at": getattr(data, "created_at", None),
            "started_at": getattr(data, "started_at", None),
            "finished_at": getattr(data, "finished_at", None),
        }

    model_config = {"from_attributes": True}


class DshHealthOut(BaseModel):
    available: bool
    reason: str = ""
