"""项目相关 Pydantic 模型。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str = ""
    status: int = 1


class ProjectCreate(BaseModel):
    code: str
    name: str
    description: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class SwitchProjectIn(BaseModel):
    project_id: int
