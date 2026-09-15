"""link execution runs to canonical campaigns

Revision ID: 20260919_execution_run_campaign
Revises: 20260918_execution_campaign
Create Date: 2026-09-15

Adds traceability columns only. Execution truth stays in execution_runs and
Campaign remains orchestration-only.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260919_execution_run_campaign"
down_revision: Union[str, None] = "20260918_execution_campaign"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_runs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("execution_runs")}
    if "campaign_id" not in columns:
        op.add_column("execution_runs", sa.Column("campaign_id", sa.Integer(), nullable=True))
    if "campaign_item_id" not in columns:
        op.add_column("execution_runs", sa.Column("campaign_item_id", sa.Integer(), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("execution_runs")}
    if "ix_execution_runs_campaign_id" not in indexes:
        op.create_index("ix_execution_runs_campaign_id", "execution_runs", ["campaign_id"])
    if "ix_execution_runs_campaign_item_id" not in indexes:
        op.create_index(
            "ix_execution_runs_campaign_item_id", "execution_runs", ["campaign_item_id"]
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "execution_runs" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("execution_runs")}
    if "ix_execution_runs_campaign_item_id" in indexes:
        op.drop_index("ix_execution_runs_campaign_item_id", table_name="execution_runs")
    if "ix_execution_runs_campaign_id" in indexes:
        op.drop_index("ix_execution_runs_campaign_id", table_name="execution_runs")
    columns = {column["name"] for column in inspector.get_columns("execution_runs")}
    if "campaign_item_id" in columns:
        op.drop_column("execution_runs", "campaign_item_id")
    if "campaign_id" in columns:
        op.drop_column("execution_runs", "campaign_id")
