"""aitde v3 scenario tables

Revision ID: 20260829_aitde_scenario
Revises: 20260829_aitde_contract
Create Date: 2026-08-29 00:00:00

AITDE V3 (EPIC-06 / V30-060, M3-scenario): introduce test_scenarios,
test_scenario_versions and test_oracles.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_scenario"
down_revision: Union[str, None] = "20260829_aitde_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test_scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("mission_id", sa.Integer, nullable=False, index=True),
        sa.Column("scenario_key", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("current_version_no", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("mission_id", "scenario_key", name="uq_scenario_mission_key"),
    )

    op.create_table(
        "test_scenario_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("scenario_id", sa.Integer, nullable=False, index=True),
        sa.Column("version_no", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("contract_version_id", sa.Integer, nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("business_goal", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("priority", sa.String(4), nullable=False, server_default=sa.text("'P2'")),
        sa.Column("risk_level", sa.String(4), nullable=False, server_default=sa.text("'P2'")),
        sa.Column("given_model_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("when_model_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expected_state_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("review_status", sa.String(16), nullable=False, server_default=sa.text("'PROPOSED'"), index=True),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("approved_by", sa.Integer, nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("supersedes_version_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("scenario_id", "version_no", name="uq_scenario_version_no"),
    )

    op.create_table(
        "test_oracles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("scenario_version_id", sa.Integer, nullable=False, index=True),
        sa.Column("oracle_key", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("oracle_type", sa.String(16), nullable=False, server_default=sa.text("'DB'")),
        sa.Column("target_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("operator", sa.String(32), nullable=False, server_default=sa.text("'eq'")),
        sa.Column("expected_value_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_type", sa.String(32), nullable=False, server_default=sa.text("'REQUIREMENT_EXPLICIT'")),
        sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("required", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("1")),
        sa.Column("review_status", sa.String(16), nullable=False, server_default=sa.text("'PROPOSED'")),
        sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("reviewed_by", sa.Integer, nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("test_oracles")
    op.drop_table("test_scenario_versions")
    op.drop_table("test_scenarios")
