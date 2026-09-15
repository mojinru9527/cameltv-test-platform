"""execution canonical campaign orchestration tables

Revision ID: 20260918_execution_campaign
Revises: 20260917_b236_ai_shadow_run
Create Date: 2026-09-15

Adds the PR-01 orchestration layer only. Execution truth remains in the
existing AITDE execution_runs table; no second Run/queue/state machine is
introduced.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260918_execution_campaign"
down_revision: Union[str, None] = "20260917_b236_ai_shadow_run"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "test_campaign" not in tables:
        op.create_table(
            "test_campaign",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("name", sa.String(200), nullable=False, server_default=sa.text("''")),
            sa.Column("type", sa.String(32), nullable=False, server_default=sa.text("'adhoc'")),
            sa.Column("requirement_version", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("environment_id", sa.Integer(), nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("dataset_id", sa.Integer(), nullable=True),
            sa.Column("runner_selector_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("strategy_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'"), index=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_by", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("project_id", "name", "version", name="uq_campaign_project_name_version"),
        )

    if "test_campaign_item" not in tables:
        op.create_table(
            "test_campaign_item",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("test_campaign.id"), nullable=False, index=True),
            sa.Column("asset_type", sa.String(32), nullable=False, index=True),
            sa.Column("asset_id", sa.Integer(), nullable=False, index=True),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("depends_on_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("config_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.UniqueConstraint("campaign_id", "sequence", name="uq_campaign_item_sequence"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "test_campaign_item" in tables:
        op.drop_table("test_campaign_item")
    if "test_campaign" in tables:
        op.drop_table("test_campaign")
