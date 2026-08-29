"""aitde v3.3 healing_proposals

Revision ID: 20260829_aitde_v33_healing
Revises: 20260829_aitde_v33_manual
Create Date: 2026-08-29 19:20:00

AITDE V3.3 (V33-011): durable Action Healing proposals. Persists the outcome of
the HealingGuard diff so a reviewer can list / approve / reject a proposal and
the audit trail (before/after IR, reason, evidence refs, reviewer) survives a
refresh.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v33_healing"
down_revision: Union[str, None] = "20260829_aitde_v33_manual"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "healing_proposals" not in inspector.get_table_names():
        op.create_table(
            "healing_proposals",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("scenario_adapter_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("command_plan_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("proposal_type", sa.String(32), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("before_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("after_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("reason", sa.Text, nullable=False, server_default=sa.text("''")),
            sa.Column("evidence_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'OPEN'"), index=True),
            sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'AI'")),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("reviewed_by", sa.Integer, nullable=True),
            sa.Column("reviewed_at", sa.DateTime, nullable=True),
        )


def downgrade() -> None:
    op.drop_table("healing_proposals")
