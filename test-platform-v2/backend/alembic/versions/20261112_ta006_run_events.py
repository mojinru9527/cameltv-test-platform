"""M1 / TA-006：run_events + event_outbox 迁移

Revision ID: 20261112_ta006_run_events
Revises: 20261111_ta005_run_models

初始迁移 20260616_0001 使用 Base.metadata.create_all()，在 SQLite/全新库上会预建
本迁移的两张表；检测到 run_events 已含 seq 列时直接返回（与 batch-279 同策略）。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261112_ta006_run_events"
down_revision = "20261111_ta005_run_models"
branch_labels = None
depends_on = None


def _outbox_id_type() -> sa.types.TypeEngine:
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    if "run_events" in existing:
        cols = {c["name"] for c in inspector.get_columns("run_events")}
        if "seq" in cols:
            return
        for legacy in ("event_outbox", "run_events"):
            if legacy in existing:
                if bind.dialect.name == "postgresql":
                    op.execute(f'DROP TABLE IF EXISTS "{legacy}" CASCADE')
                else:
                    op.drop_table(legacy)

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("node_run_id", sa.String(length=36), nullable=True),
        sa.Column("step_attempt_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("producer", sa.String(length=80), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("producer_event_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_run_id"], ["node_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["step_attempt_id"], ["step_attempts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "seq", name="uq_run_events_run_seq"),
        sa.UniqueConstraint(
            "run_id", "producer_event_id", name="uq_run_events_run_producer_event"
        ),
    )
    op.create_index("ix_run_events_run_seq", "run_events", ["run_id", "seq"])

    op.create_table(
        "event_outbox",
        sa.Column("id", _outbox_id_type(), autoincrement=True, nullable=False),
        sa.Column("run_event_id", sa.String(length=36), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_event_id"], ["run_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_event_id", name="uq_event_outbox_run_event"),
    )


def downgrade() -> None:
    op.drop_table("event_outbox")
    op.drop_index("ix_run_events_run_seq", table_name="run_events")
    op.drop_table("run_events")
