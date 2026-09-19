"""impact_edge table (Batch 260 / B3-1)

Revision ID: 20260925_batch260_impact_edges
Revises: 20260924_batch258_execution_payload
Create Date: 2026-09-19

新增"变更/覆盖/依赖"影响图边表。与既有 `interaction_edge`（交互拓扑，3172 条）
**语义不同、不合并**：前者回答"改了 X 要重测什么"，后者回答"用户怎么走"。
唯一约束 (project_id, source_ref, target_ref, kind, version) 保证关联构建可反复执行而幂等。

写迁移前已确认（cameltv-bug-guard）：
  1. `ls alembic/versions/` 中不存在 `impact_edge` 表或同名列；
  2. DDL 用独立临时 SQLite 走 from-base 与单步 downgrade 校验，未使用 dev 库。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260925_batch260_impact_edges"
down_revision: Union[str, None] = "20260924_batch258_execution_payload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "impact_edge" in set(inspector.get_table_names()):
        return
    op.create_table(
        "impact_edge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("source_ref", sa.String(200), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("target_ref", sa.String(200), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("version", sa.String(80), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "project_id",
            "source_ref",
            "target_ref",
            "kind",
            "version",
            name="uq_impact_edge_key",
        ),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "impact_edge" in set(inspector.get_table_names()):
        op.drop_table("impact_edge")
