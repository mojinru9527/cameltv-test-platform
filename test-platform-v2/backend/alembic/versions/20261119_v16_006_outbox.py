"""V16-006: AIQE outbox (same-transaction event, idempotent relay)

Revision ID: 20261119_v16_006_outbox
Revises: 20261119_v16_007_snapshot
Create Date: 2026-11-19 22:10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_006_outbox"
down_revision: Union[str, None] = "20261119_v16_007_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_outbox_events" in inspector.get_table_names():
        return
    op.create_table(
        "aiqe_outbox_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("producer_event_id", sa.String(length=160), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_aiqe_outbox_producer_event",
        "aiqe_outbox_events",
        ["producer_event_id"],
        unique=True,
    )
    op.create_index("ix_aiqe_outbox_events_status", "aiqe_outbox_events", ["status"])
    op.create_index("ix_aiqe_outbox_events_project_id", "aiqe_outbox_events", ["project_id"])
    op.create_index("ix_aiqe_outbox_events_run_id", "aiqe_outbox_events", ["run_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_outbox_events" not in inspector.get_table_names():
        return
    for name in (
        "ix_aiqe_outbox_events_run_id",
        "ix_aiqe_outbox_events_project_id",
        "ix_aiqe_outbox_events_status",
        "uq_aiqe_outbox_producer_event",
    ):
        op.drop_index(name, table_name="aiqe_outbox_events")
    op.drop_table("aiqe_outbox_events")
