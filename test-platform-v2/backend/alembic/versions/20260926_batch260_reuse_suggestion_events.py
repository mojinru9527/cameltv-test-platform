"""reuse_suggestion_event table (Batch 260 / B3-4)

Revision ID: 20260926_batch260_reuse_suggestion_events
Revises: 20260925_batch260_impact_edges
Create Date: 2026-09-19

复用建议命中率埋点表。B11/B12 已能"自动带出上一版经验"，但没有地方记录
"带出了什么、最后采纳没有"，导致 09 §2.3 的「复用建议命中率 ≥50%」无法计算。

写迁移前已确认（cameltv-bug-guard）：
  1. `ls alembic/versions/` 中不存在 `reuse_suggestion_event` 表或同名列；
  2. DDL 用独立临时 SQLite 走 from-base 与单步 downgrade 校验，未使用 dev 库。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_batch260_reuse_suggestion_events"
down_revision: Union[str, None] = "20260925_batch260_impact_edges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "reuse_suggestion_event" in set(inspector.get_table_names()):
        return
    op.create_table(
        "reuse_suggestion_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("task_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("suggestion_ref", sa.String(200), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("title", sa.String(300), nullable=False, server_default=sa.text("''")),
        sa.Column("decision", sa.String(20), nullable=False, server_default=sa.text("'suggested'"), index=True),
        sa.Column("decided_by", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "task_id", "suggestion_ref", "decision", name="uq_reuse_suggestion_event"
        ),
    )
    op.create_index(
        "ix_reuse_suggestion_project_task",
        "reuse_suggestion_event",
        ["project_id", "task_id"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "reuse_suggestion_event" in set(inspector.get_table_names()):
        op.drop_table("reuse_suggestion_event")
