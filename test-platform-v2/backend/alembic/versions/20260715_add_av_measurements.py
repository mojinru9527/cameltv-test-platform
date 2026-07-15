"""Add real AV measurement records.

Revision ID: 20260715_add_av_measurements
Revises: 20260715_test_case_api_cols
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_add_av_measurements"
down_revision: Union[str, None] = "20260715_test_case_api_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "av_check_measurement",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("av_check_task.id"), nullable=False),
        sa.Column("metric_type", sa.String(40), nullable=False),
        sa.Column("scenario", sa.String(200), nullable=False, server_default=""),
        sa.Column("method", sa.String(100), nullable=False, server_default=""),
        sa.Column("environment", sa.String(100), nullable=False, server_default=""),
        sa.Column("device_info", sa.String(500), nullable=False, server_default=""),
        sa.Column("network_condition", sa.String(500), nullable=False, server_default=""),
        sa.Column("unit", sa.String(20), nullable=False, server_default=""),
        sa.Column("samples_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0"),
        sa.Column("comparator", sa.String(4), nullable=False, server_default="<="),
        sa.Column("stats_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("pass_basis", sa.String(20), nullable=False, server_default="mean"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("creator_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_av_check_measurement_task_id", "av_check_measurement", ["task_id"])
    op.create_index("ix_av_check_measurement_metric_type", "av_check_measurement", ["metric_type"])


def downgrade() -> None:
    op.drop_index("ix_av_check_measurement_metric_type", table_name="av_check_measurement")
    op.drop_index("ix_av_check_measurement_task_id", table_name="av_check_measurement")
    op.drop_table("av_check_measurement")
