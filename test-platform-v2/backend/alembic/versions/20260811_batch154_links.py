"""batch154_remaining_links

Revision ID: 20260811_batch154_links
Revises: 20260811_batch151_auto_defect
Create Date: 2026-08-11

C147-8: test_case.dataset_id（默认数据集绑定）
C151-1: ui_test_job.case_id（UI 任务↔用例映射）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260811_batch154_links"
down_revision: Union[str, None] = "20260811_batch151_auto_defect"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str] | None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if table not in inspector.get_table_names():
        return None
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    tc = _columns("test_case")
    if tc is not None and "dataset_id" not in tc:
        op.add_column("test_case", sa.Column("dataset_id", sa.Integer(), nullable=True))
    uj = _columns("ui_test_job")
    if uj is not None and "case_id" not in uj:
        op.add_column("ui_test_job", sa.Column("case_id", sa.Integer(), nullable=True))
        op.create_index("ix_ui_test_job_case_id", "ui_test_job", ["case_id"])


def downgrade() -> None:
    uj = _columns("ui_test_job")
    if uj is not None and "case_id" in uj:
        op.drop_index("ix_ui_test_job_case_id", table_name="ui_test_job")
        op.drop_column("ui_test_job", "case_id")
    tc = _columns("test_case")
    if tc is not None and "dataset_id" in tc:
        op.drop_column("test_case", "dataset_id")
