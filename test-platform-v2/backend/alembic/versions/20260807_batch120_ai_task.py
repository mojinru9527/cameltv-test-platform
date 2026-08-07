"""batch120_ai_task

Revision ID: 20260807_batch120_ai_task
Revises: 20260807_batch115_tc_depends
Create Date: 2026-08-07

C117-2：AI 异步任务 DB 队列（多 worker 可消费）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260807_batch120_ai_task"
down_revision: Union[str, None] = "20260807_batch115_tc_depends"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    import sqlalchemy as _sa
    if "ai_task" in _sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "ai_task",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_type", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("document_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="null"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_task_status", "ai_task", ["status"])
    op.create_index("ix_ai_task_project_id", "ai_task", ["project_id"])


def downgrade() -> None:
    bind = op.get_bind()
    import sqlalchemy as _sa
    if "ai_task" not in _sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_ai_task_status", table_name="ai_task")
    op.drop_index("ix_ai_task_project_id", table_name="ai_task")
    op.drop_table("ai_task")
