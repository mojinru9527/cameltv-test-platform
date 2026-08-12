"""batch155_schedule_disabled_reason

Revision ID: 20260811_b155_sched_reason
Revises: 20260811_batch154_links
Create Date: 2026-08-11

P2-18: test_schedule.disabled_reason（调度停用原因）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260811_b155_sched_reason"
down_revision: Union[str, None] = "20260811_batch154_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "test_schedule" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("test_schedule")}
    if "disabled_reason" not in columns:
        op.add_column("test_schedule", sa.Column("disabled_reason", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "test_schedule" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("test_schedule")}
    if "disabled_reason" in columns:
        op.drop_column("test_schedule", "disabled_reason")

