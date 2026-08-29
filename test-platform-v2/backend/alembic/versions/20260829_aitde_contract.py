"""aitde v3 contract tables

Revision ID: 20260829_aitde_contract
Revises: 20260829_aitde_scope
Create Date: 2026-08-29 00:00:00

AITDE V3 (EPIC-05 / V30-050, M3-contract): introduce test_contracts,
test_contract_versions and change_proposals.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_contract"
down_revision: Union[str, None] = "20260829_aitde_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "test_contracts" in inspector.get_table_names():
        return

    op.create_table(
        "test_contracts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("current_version_no", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("mission_id", name="uq_contract_mission"),
    )

    op.create_table(
        "test_contract_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("contract_id", sa.Integer, nullable=False, index=True),
        sa.Column("version_no", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("snapshot_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("supersedes_version_id", sa.Integer, nullable=True),
        sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("approved_by", sa.Integer, nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("contract_id", "version_no", name="uq_contract_version_no"),
    )

    op.create_table(
        "change_proposals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, nullable=False, index=True),
        sa.Column("target_type", sa.String(16), nullable=False, server_default=sa.text("'CONTRACT'")),
        sa.Column("target_id", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("target_version", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("proposal_type", sa.String(32), nullable=False, server_default=sa.text("'modify'")),
        sa.Column("reason", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("diff_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'OPEN'"), index=True),
        sa.Column("reviewed_by", sa.Integer, nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("change_proposals")
    op.drop_table("test_contract_versions")
    op.drop_table("test_contracts")
