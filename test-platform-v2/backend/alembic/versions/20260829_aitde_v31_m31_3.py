"""aitde v3.1 M31-3: evidence_artifacts + replay_manifests + legacy_execution_links

Revision ID: 20260829_aitde_v31_m31_3
Revises: 20260829_aitde_v31_m31_2
Create Date: 2026-08-29 01:00:00

AITDE V3.1 (V31-003/V31-004): evidence metadata (raw bytes live in object
storage), append-only proof replay manifest, and the legacy API/UI execution
bridge link table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v31_m31_3"
down_revision: Union[str, None] = "20260829_aitde_v31_m31_2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "evidence_artifacts" not in inspector.get_table_names():
        op.create_table(
            "evidence_artifacts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("step_id", sa.Integer, nullable=True),
            sa.Column("evidence_type", sa.String(32), nullable=False, server_default=sa.text("'RESPONSE'"), index=True),
            sa.Column("storage_provider", sa.String(32), nullable=False, server_default=sa.text("'local'")),
            sa.Column("storage_uri", sa.String(512), nullable=False, server_default=sa.text("''")),
            sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("content_type", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("size_bytes", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("sanitization_status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("sensitivity", sa.String(16), nullable=False, server_default=sa.text("'normal'")),
            sa.Column("retention_class", sa.String(32), nullable=False, server_default=sa.text("'standard'")),
            sa.Column("created_at", sa.DateTime, nullable=True),
        )

    if "replay_manifests" not in inspector.get_table_names():
        op.create_table(
            "replay_manifests",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("schema_version", sa.String(16), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("manifest_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("manifest_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("generated_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("run_id", name="uq_replay_manifest_run"),
        )

    if "legacy_execution_links" not in inspector.get_table_names():
        op.create_table(
            "legacy_execution_links",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("legacy_type", sa.String(32), nullable=False, server_default=sa.text("'API_TASK_ITEM'"), index=True),
            sa.Column("legacy_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.UniqueConstraint("legacy_type", "legacy_id", name="uq_legacy_execution_link"),
        )


def downgrade() -> None:
    op.drop_table("legacy_execution_links")
    op.drop_table("replay_manifests")
    op.drop_table("evidence_artifacts")
