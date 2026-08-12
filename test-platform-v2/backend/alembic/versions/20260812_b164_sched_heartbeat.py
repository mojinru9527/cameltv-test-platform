"""batch-164 C163-1: test_schedule_run.heartbeat_at

Revision ID: 20260812_b164_sched_heartbeat
Revises: 20260812_b162_sched_env
Create Date: 2026-08-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260812_b164_sched_heartbeat"
down_revision = "20260812_b162_sched_env"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    return column in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "test_schedule_run"):
        return
    if not _has_column(bind, "test_schedule_run", "heartbeat_at"):
        op.add_column("test_schedule_run", sa.Column("heartbeat_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "test_schedule_run"):
        return
    if _has_column(bind, "test_schedule_run", "heartbeat_at"):
        op.drop_column("test_schedule_run", "heartbeat_at")
