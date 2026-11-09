"""M1 / TA-007：run_artifacts 迁移

Revision ID: 20261113_ta007_run_artifacts
Revises: 20261112_ta006_run_events

初始迁移 create_all 会在全新库预建本表；检测 sha256 列后跳过（同 279/280 策略）。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261113_ta007_run_artifacts"
down_revision = "20261112_ta006_run_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    if "run_artifacts" in existing:
        cols = {c["name"] for c in inspector.get_columns("run_artifacts")}
        if "sha256" in cols:
            return
        if bind.dialect.name == "postgresql":
            op.execute('DROP TABLE IF EXISTS "run_artifacts" CASCADE')
        else:
            op.drop_table("run_artifacts")

    op.create_table(
        "run_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("node_run_id", sa.String(length=36), nullable=True),
        sa.Column("step_attempt_id", sa.String(length=36), nullable=True),
        sa.Column("artifact_type", sa.String(length=24), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "mime_type",
            sa.String(length=100),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column(
            "redaction_status", sa.String(length=16), nullable=False, server_default="pending"
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("linked_evidence_type", sa.String(length=32), nullable=True),
        sa.Column("linked_evidence_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_run_id"], ["node_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["step_attempt_id"], ["step_attempts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_artifacts_run_created", "run_artifacts", ["run_id", "created_at"])
    op.create_index("ix_run_artifacts_sha256", "run_artifacts", ["sha256"])
    op.create_index("ix_run_artifacts_redaction", "run_artifacts", ["redaction_status"])
    op.create_index("ix_run_artifacts_node_run", "run_artifacts", ["node_run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_artifacts_node_run", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_redaction", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_sha256", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_run_created", table_name="run_artifacts")
    op.drop_table("run_artifacts")
