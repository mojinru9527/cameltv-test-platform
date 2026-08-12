"""batch-162 C161-2: test_schedule.environment_id

Revision ID: 20260812_b162_sched_env
Revises: 20260812_batch157_exec_link
Create Date: 2026-08-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260812_b162_sched_env"
down_revision = "20260812_batch157_exec_link"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    return column in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    # 与仓库迁移约定一致：test_schedule 可能由 AUTO_CREATE_TABLES（模型元数据）建表，
    # 干净检出/裸库场景下也可能不存在 → 幂等处理，避免 duplicate column。
    bind = op.get_bind()
    if not _has_table(bind, "test_schedule"):
        return
    if not _has_column(bind, "test_schedule", "environment_id"):
        op.add_column("test_schedule", sa.Column("environment_id", sa.Integer(), nullable=True))
    indexes = {i["name"] for i in sa.inspect(bind).get_indexes("test_schedule")}
    if "ix_test_schedule_environment_id" not in indexes:
        op.create_index("ix_test_schedule_environment_id", "test_schedule", ["environment_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "test_schedule"):
        return
    indexes = {i["name"] for i in sa.inspect(bind).get_indexes("test_schedule")}
    if "ix_test_schedule_environment_id" in indexes:
        op.drop_index("ix_test_schedule_environment_id", table_name="test_schedule")
    if _has_column(bind, "test_schedule", "environment_id"):
        op.drop_column("test_schedule", "environment_id")
