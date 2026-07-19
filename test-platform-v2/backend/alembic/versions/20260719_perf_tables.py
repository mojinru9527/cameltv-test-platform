"""Add perf session/metric/device tables for client-side performance monitoring.

Revision ID: 20260719_perf_tables
Revises: 20260716_case_cleanup
Create Date: 2026-07-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_perf_tables"
down_revision: Union[str, None] = "20260716_case_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())

    # ── perf_device ──
    if "perf_device" not in existing:
        op.create_table(
            "perf_device",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("device_id", sa.String(200), unique=True, index=True),
            sa.Column("device_name", sa.String(200), server_default=""),
            sa.Column("device_model", sa.String(100), server_default=""),
            sa.Column("platform", sa.String(20), server_default="Android"),
            sa.Column("os_version", sa.String(50), server_default=""),
            sa.Column("status", sa.String(20), server_default="online"),
            sa.Column("last_seen_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # ── perf_session ──
    if "perf_session" not in existing:
        op.create_table(
            "perf_session",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), index=True, server_default="0"),
            sa.Column("session_id", sa.String(50), index=True, server_default=""),
            sa.Column("device_id", sa.String(200), server_default=""),
            sa.Column("device_name", sa.String(200), server_default=""),
            sa.Column("device_model", sa.String(100), server_default=""),
            sa.Column("platform", sa.String(20), server_default="Android"),
            sa.Column("pkg_name", sa.String(200), server_default=""),
            sa.Column("metrics", sa.String(200), server_default=""),
            sa.Column("status", sa.String(20), server_default="pending"),
            sa.Column("duration", sa.Integer(), server_default="300"),
            sa.Column("actual_duration_s", sa.Integer(), server_default="0"),
            sa.Column("summary_json", sa.Text(), server_default="{}"),
            sa.Column("error_message", sa.Text(), server_default=""),
            sa.Column("creator_id", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # ── perf_metric ──
    if "perf_metric" not in existing:
        op.create_table(
            "perf_metric",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("perf_session.id"), index=True),
            sa.Column("timestamp", sa.Float(), index=True, server_default="0.0"),
            sa.Column("elapsed_s", sa.Float(), server_default="0.0"),
            sa.Column("metric_type", sa.String(20), server_default="snapshot"),
            sa.Column("data_json", sa.Text(), server_default="{}"),
        )


def downgrade() -> None:
    op.drop_table("perf_metric")
    op.drop_table("perf_session")
    op.drop_table("perf_device")
