"""automation_task_worker — 持久化任务 worker 字段

为 api_execution_task 增加取消、重试、锁、超时字段。
为 api_execution_task_item 增加错误类型、重试、执行时间字段。

Revision ID: 20260713_automation_task_worker
Revises: 20260710_0017
Create Date: 2026-07-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260713_automation_task_worker"
down_revision: Union[str, None] = "20260710_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns_by_table = {
        table_name: {
            column["name"]
            for column in inspector.get_columns(table_name)
        }
        for table_name in ("api_execution_task", "api_execution_task_item")
    }

    def add_column_if_missing(table_name: str, column: sa.Column) -> None:
        if column.name not in columns_by_table[table_name]:
            op.add_column(table_name, column)

    # api_execution_task — worker governance columns
    add_column_if_missing("api_execution_task", sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
    add_column_if_missing("api_execution_task", sa.Column("confirm_prod", sa.Boolean(), nullable=False, server_default=sa.false()))
    add_column_if_missing("api_execution_task", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    add_column_if_missing("api_execution_task", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="1"))
    add_column_if_missing("api_execution_task", sa.Column("locked_at", sa.DateTime(), nullable=True))
    add_column_if_missing("api_execution_task", sa.Column("locked_by", sa.String(), nullable=False, server_default=""))
    add_column_if_missing("api_execution_task", sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="1800"))

    # api_execution_task_item — per-item execution tracking columns
    add_column_if_missing("api_execution_task_item", sa.Column("error_type", sa.String(), nullable=False, server_default=""))
    add_column_if_missing("api_execution_task_item", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    add_column_if_missing("api_execution_task_item", sa.Column("started_at", sa.DateTime(), nullable=True))
    add_column_if_missing("api_execution_task_item", sa.Column("finished_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("api_execution_task_item", "finished_at")
    op.drop_column("api_execution_task_item", "started_at")
    op.drop_column("api_execution_task_item", "retry_count")
    op.drop_column("api_execution_task_item", "error_type")

    op.drop_column("api_execution_task", "timeout_seconds")
    op.drop_column("api_execution_task", "locked_by")
    op.drop_column("api_execution_task", "locked_at")
    op.drop_column("api_execution_task", "max_retries")
    op.drop_column("api_execution_task", "retry_count")
    op.drop_column("api_execution_task", "confirm_prod")
    op.drop_column("api_execution_task", "cancel_requested")
