"""ImpactEdge —— 变更/覆盖/依赖关系图（Batch 260 / B3-1）。

**与 `InteractionEdge` 的分工（两张边表语义不同，不合并）**

| | `InteractionEdge` | `ImpactEdge`（本表） |
|---|---|---|
| 回答的问题 | 用户**怎么走**（页面/入口跳转拓扑） | 改了 X **要重测什么**（变更/覆盖/依赖） |
| 字段形状 | from_module / entry / to / evidence / source_batch | source_ref / target_ref / kind / version / confidence |
| 数据来源 | batch-113 交互拓扑入库（3172 条） | 需求变更 → 模块 → 用例 → 执行（B3-2 构建） |
| 引入批次 | C120-1 | Batch 260（B3） |

两者**不互相冒充**：交互拓扑用于"覆盖缺口"问答的输入之一，影响图用于回答"改了 X 要跑哪些"。
合并会让"这是用户路径还是影响关系"无法区分——那正是双栈漂移的起点。

`kind` 只有三种（见 `EDGE_KINDS`）：
  - `changed`：某版本**改动**了某模块/需求；
  - `covers` ：某用例**覆盖**某模块/端点；
  - `depends`：某对象**依赖**另一对象。
"""
from __future__ import annotations

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin

EDGE_KINDS = frozenset({"changed", "covers", "depends"})


class ImpactEdge(Base, TimestampMixin):
    """变更/覆盖/依赖边：回答「改了 X 要重测什么」。

    与 `InteractionEdge`（交互拓扑，回答「用户怎么走」）语义不同、不合并；
    详细分工见本模块 docstring 的对照表。
    """

    __tablename__ = "impact_edge"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "source_ref",
            "target_ref",
            "kind",
            "version",
            name="uq_impact_edge_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    source_ref: Mapped[str] = mapped_column(String(200), default="", index=True)
    target_ref: Mapped[str] = mapped_column(String(200), default="", index=True)
    kind: Mapped[str] = mapped_column(String(20), default="", index=True)
    version: Mapped[str] = mapped_column(String(80), default="", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
