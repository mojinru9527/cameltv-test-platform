"""batch151_auto_defect_on_fail

Revision ID: 20260811_batch151_auto_defect
Revises: 20260811_batch148_exec_err
Create Date: 2026-08-11

C147-6: test_plan.auto_defect_on_fail（失败自动转缺陷/报告/通知开关）。
Batch 154 补录：该迁移随 Batch 151 合并时遗漏（PR #209 未包含迁移文件），
模型/服务已上线，本文件补回使 fresh DB 升级链路完整（幂等守卫）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260811_batch151_auto_defect"
down_revision: Union[str, None] = "20260811_batch148_exec_err"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "test_plan" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("test_plan")}
    if "auto_defect_on_fail" not in columns:
        op.add_column(
            "test_plan",
            sa.Column("auto_defect_on_fail", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "test_plan" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("test_plan")}
    if "auto_defect_on_fail" in columns:
        op.drop_column("test_plan", "auto_defect_on_fail")
