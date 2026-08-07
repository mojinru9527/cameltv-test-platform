"""batch115_tc_depends

Revision ID: 20260807_batch115_test_case_depends
Revises: 20260807_batch115_ui_schedule
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260807_batch115_tc_depends"
down_revision: Union[str, None] = "20260807_batch115_ui_schedule"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    import sqlalchemy as _sa
    insp = _sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    # C107-2：接口用例前置依赖（depends_on_ids JSON 数组）；幂等（CI 模型建表场景跳过）
    bind = op.get_bind()
    if not _has_column(bind, "test_case", "depends_on_ids"):
        op.add_column("test_case", sa.Column("depends_on_ids", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "test_case", "depends_on_ids"):
        op.drop_column("test_case", "depends_on_ids")