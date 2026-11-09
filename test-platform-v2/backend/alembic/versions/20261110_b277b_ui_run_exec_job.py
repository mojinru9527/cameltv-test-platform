"""Batch 277b / P0-4: link UiTestRun to the node ExecutionJob.

node 模式下 /uitest 不再在控制面起浏览器，而是派发 ExecutionJob(kind="ui")；
run 通过 execution_job_id 投影节点执行状态与证据目录。

Revision ID: 20261110_b277b_ui_run_exec_job
Revises: 20261109_b277_drop_retired_tables
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261110_b277b_ui_run_exec_job"
down_revision: Union[str, None] = "20261109_b277_drop_retired_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("ui_test_run", "execution_job_id"):
        op.add_column("ui_test_run", sa.Column("execution_job_id", sa.BigInteger(), nullable=True))
    inspector = sa.inspect(op.get_bind())
    indexes = {i["name"] for i in inspector.get_indexes("ui_test_run")}
    if "ix_ui_test_run_execution_job_id" not in indexes:
        op.create_index(
            "ix_ui_test_run_execution_job_id",
            "ui_test_run",
            ["execution_job_id"],
            if_not_exists=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {i["name"] for i in inspector.get_indexes("ui_test_run")}
    if "ix_ui_test_run_execution_job_id" in indexes:
        op.drop_index("ix_ui_test_run_execution_job_id", table_name="ui_test_run")
    if _has_column("ui_test_run", "execution_job_id"):
        with op.batch_alter_table("ui_test_run") as batch:
            batch.drop_column("execution_job_id")
