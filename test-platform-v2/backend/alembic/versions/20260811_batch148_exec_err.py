"""batch148_test_execution_error_fields

Revision ID: 20260811_batch148_exec_err
Revises: 20260808_batch121_topo_edges
Create Date: 2026-08-11

C147-2: test_execution 增加 status_code / error_type / error_message 独立字段，
执行历史 UI 直接展示失败根因；历史行由 service 层从 actual_result JSON 回填解析。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260811_batch148_exec_err"
down_revision: Union[str, None] = "20260808_batch121_topo_edges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns() -> set[str]:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "test_execution" not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns("test_execution")}


def upgrade() -> None:
    cols = _existing_columns()
    if "status_code" not in cols:
        op.add_column(
            "test_execution",
            sa.Column("status_code", sa.Integer(), nullable=False, server_default="0"),
        )
    if "error_type" not in cols:
        op.add_column(
            "test_execution",
            sa.Column("error_type", sa.String(length=50), nullable=False, server_default=""),
        )
    if "error_message" not in cols:
        op.add_column(
            "test_execution",
            sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        )


def downgrade() -> None:
    cols = _existing_columns()
    for col in ("error_message", "error_type", "status_code"):
        if col in cols:
            op.drop_column("test_execution", col)
