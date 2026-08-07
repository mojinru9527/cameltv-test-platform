"""C114-1 交互拓扑覆盖缺口提示 schema。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InteractionEdge(BaseModel):
    """一条交互拓扑边。"""
    model_config = ConfigDict(populate_by_name=True)

    from_module: str = Field(default="", description="来源模块")
    entry: str = Field(default="", description="入口/链接文本")
    to: str = Field(default="", description="目标 URL/路径")
    from_url: str = Field(default="", alias="from", description="来源 URL/路径")


class InteractionGapRequest(BaseModel):
    """交互拓扑边清单请求体。"""
    edges: list[InteractionEdge] = Field(default_factory=list, description="交互拓扑边")
