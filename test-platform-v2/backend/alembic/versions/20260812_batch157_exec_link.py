"""batch157_execution_model_link

Revision ID: 20260812_batch157_exec_link
Revises: 20260811_b155_sched_reason
Create Date: 2026-08-12

Batch 157：执行模型双向关联
- test_execution.api_task_id（计划 API 执行 → API 任务）
- api_execution_task_item.test_execution_id（API 任务明细 → 计划执行）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_batch157_exec_link"
down_revision: Union[str, None] = "20260811_b155_sched_reason"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "test_execution" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("test_execution")}
        if "api_task_id" not in columns:
            op.add_column("test_execution", sa.Column("api_task_id", sa.Integer(), nullable=True))
    if "api_execution_task_item" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("api_execution_task_item")}
        if "test_execution_id" not in columns:
            op.add_column("api_execution_task_item", sa.Column("test_execution_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "test_execution" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("test_execution")}
        if "api_task_id" in columns:
            op.drop_column("test_execution", "api_task_id")
    if "api_execution_task_item" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("api_execution_task_item")}
        if "test_execution_id" in columns:
            op.drop_column("api_execution_task_item", "test_execution_id")
