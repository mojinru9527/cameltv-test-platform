"""batch-167 version coverage pipeline: requirement sources + bundle access config

Revision ID: 20260813_b167_version_coverage
Revises: 20260812_b164_sched_heartbeat
Create Date: 2026-08-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260813_b167_version_coverage"
down_revision = "20260812_b164_sched_heartbeat"
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, column: str) -> bool:
    if not _has_table(bind, table):
        return False
    return column in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    # requirement_document: fetched source URL + extraction quality metadata
    if not _has_column(bind, "requirement_document", "source_url"):
        op.add_column("requirement_document", sa.Column("source_url", sa.Text(), nullable=False, server_default=""))
    if not _has_column(bind, "requirement_document", "extraction_meta"):
        op.add_column("requirement_document", sa.Column("extraction_meta", sa.Text(), nullable=False, server_default="{}"))

    # release_bundle: version-level test access config
    for col in ("requirement_url", "user_env_url", "api_spec_url", "admin_env_url"):
        if not _has_column(bind, "release_bundle", col):
            op.add_column("release_bundle", sa.Column(col, sa.Text(), nullable=False, server_default=""))
    if not _has_column(bind, "release_bundle", "environment_id"):
        op.add_column("release_bundle", sa.Column("environment_id", sa.Integer(), nullable=True))
        op.create_index("ix_release_bundle_environment_id", "release_bundle", ["environment_id"])

    # version_mission: API spec URL aligned with the other access fields
    if not _has_column(bind, "version_mission", "api_spec_url"):
        op.add_column("version_mission", sa.Column("api_spec_url", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    bind = op.get_bind()

    if _has_column(bind, "version_mission", "api_spec_url"):
        op.drop_column("version_mission", "api_spec_url")

    if _has_column(bind, "release_bundle", "environment_id"):
        op.drop_index("ix_release_bundle_environment_id", table_name="release_bundle")
        op.drop_column("release_bundle", "environment_id")
    for col in ("admin_env_url", "api_spec_url", "user_env_url", "requirement_url"):
        if _has_column(bind, "release_bundle", col):
            op.drop_column("release_bundle", col)

    if _has_column(bind, "requirement_document", "extraction_meta"):
        op.drop_column("requirement_document", "extraction_meta")
    if _has_column(bind, "requirement_document", "source_url"):
        op.drop_column("requirement_document", "source_url")
