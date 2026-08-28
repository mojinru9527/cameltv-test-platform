"""aitde v3 scope tables

Revision ID: 20260829_aitde_scope
Revises: 20260829_aitde_sources
Create Date: 2026-08-29 00:00:00

AITDE V3 (EPIC-03 / V30-030, M2): introduce scope_items, ambiguities and
test_intents.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_scope"
down_revision: Union[str, None] = "20260829_aitde_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scope_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, nullable=False, index=True),
        sa.Column("scope_key", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("scope_type", sa.String(32), nullable=False, server_default=sa.text("'FEATURE'")),
        sa.Column("name", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("decision", sa.String(16), nullable=False, server_default=sa.text("'INCLUDE'")),
        sa.Column("test_depth", sa.String(16), nullable=False, server_default=sa.text("'FULL'")),
        sa.Column("risk_level", sa.String(4), nullable=False, server_default=sa.text("'P2'")),
        sa.Column("reason", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("ai_confidence", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("review_status", sa.String(16), nullable=False, server_default=sa.text("'PROPOSED'"), index=True),
        sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("reviewed_by", sa.Integer, nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("mission_id", "scope_key", name="uq_scope_mission_key"),
    )

    op.create_table(
        "ambiguities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, nullable=False, index=True),
        sa.Column("ambiguity_key", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("title", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("description", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("severity", sa.String(4), nullable=False, server_default=sa.text("'P2'")),
        sa.Column("status", sa.String(24), nullable=False, server_default=sa.text("'OPEN'"), index=True),
        sa.Column("candidate_options_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("selected_option_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("ai_confidence", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("resolution_note", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("resolved_by", sa.Integer, nullable=True),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "test_intents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, nullable=False, index=True),
        sa.Column("intent_key", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("title", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("business_goal", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("required_outcomes_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("risk_level", sa.String(4), nullable=False, server_default=sa.text("'P2'")),
        sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("review_status", sa.String(16), nullable=False, server_default=sa.text("'PROPOSED'")),
        sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("reviewed_by", sa.Integer, nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("test_intents")
    op.drop_table("ambiguities")
    op.drop_table("scope_items")
