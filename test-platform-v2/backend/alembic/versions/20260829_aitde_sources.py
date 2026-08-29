"""aitde v3 source tables

Revision ID: 20260829_aitde_sources
Revises: 20260829_aitde_missions
Create Date: 2026-08-29 00:00:00

AITDE V3 (EPIC-02 / V30-020): introduce source_artifacts, source_fragments and
mission_source_links to complete the M1 (Mission + Source) migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_sources"
down_revision: Union[str, None] = "20260829_aitde_missions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create_all (initial schema migration) also creates these tables on a fresh
    # DB; skip if already present (idempotent for fresh + incremental upgrades).
    inspector = sa.inspect(op.get_bind())
    if "source_artifacts" in inspector.get_table_names():
        return

    op.create_table(
        "source_artifacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("source_type", sa.String(32), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column("provider", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("name", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("uri", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("version_label", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("sensitivity", sa.String(32), nullable=False, server_default=sa.text("'normal'")),
        sa.Column("parse_status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'"), index=True),
        sa.Column("normalized_text", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "source_fragments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("artifact_id", sa.Integer, nullable=False, index=True),
        sa.Column("fragment_key", sa.String(128), nullable=False, server_default=sa.text("''")),
        sa.Column("title", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("text", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("location_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column("sequence", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("artifact_id", "fragment_key", name="uq_source_fragment_key"),
    )

    op.create_table(
        "mission_source_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mission_id", sa.Integer, nullable=False, index=True),
        sa.Column("artifact_id", sa.Integer, nullable=False, index=True),
        sa.Column("role", sa.String(32), nullable=False, server_default=sa.text("'REQUIREMENT'")),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("mission_id", "artifact_id", name="uq_mission_source_link"),
    )


def downgrade() -> None:
    op.drop_table("mission_source_links")
    op.drop_table("source_fragments")
    op.drop_table("source_artifacts")
