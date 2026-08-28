"""aitde v3 missions table

Revision ID: 20260829_aitde_missions
Revises: 20260828_b206_environment_access
Create Date: 2026-08-29 00:00:00

AITDE V3 (EPIC-01 / V30-010): introduce the ``missions`` table replacing the
slim project-bound ``version_mission`` as the canonical test-domain aggregate.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_missions"
down_revision: Union[str, None] = "20260828_b206_environment_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("mission_key", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("mission_type", sa.String(32), nullable=False, server_default=sa.text("'VERSION'"), index=True),
        sa.Column("title", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("version_label", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'DRAFT'"), index=True),
        sa.Column("owner_id", sa.Integer, nullable=True, index=True),
        sa.Column("qa_owner_id", sa.Integer, nullable=True, index=True),
        sa.Column("default_environment_id", sa.Integer, nullable=True, index=True),
        sa.Column("current_contract_version_id", sa.Integer, nullable=True),
        sa.Column("acceptance_status", sa.String(32), nullable=False, server_default=sa.text("'NOT_EVALUATED'")),
        sa.Column("legacy_version_mission_id", sa.Integer, nullable=True, unique=True),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("archived_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("project_id", "mission_key", name="uq_mission_project_key"),
    )


def downgrade() -> None:
    op.drop_table("missions")
