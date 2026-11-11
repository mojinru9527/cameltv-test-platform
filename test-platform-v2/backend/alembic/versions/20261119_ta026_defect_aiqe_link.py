"""M4 / TA-026：defect AIQE 关联字段迁移

Revision ID: 20261119_ta026_defect_aiqe_link
Revises: 20261118_ta025_triage_experiments
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261119_ta026_defect_aiqe_link"
down_revision = "20261118_ta025_triage_experiments"
branch_labels = None
depends_on = None

COLUMNS = {
    "aiqe_run_id": sa.Column("aiqe_run_id", sa.String(length=36), nullable=True),
    "aiqe_node_run_id": sa.Column("aiqe_node_run_id", sa.String(length=36), nullable=True),
    "reproduction_steps_json": sa.Column("reproduction_steps_json", sa.JSON(), nullable=True),
    "evidence_refs_json": sa.Column("evidence_refs_json", sa.JSON(), nullable=True),
    "ac_refs_json": sa.Column("ac_refs_json", sa.JSON(), nullable=True),
    "is_draft": sa.Column(
        "is_draft", sa.Boolean(), nullable=False, server_default=sa.false()
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("defect")}
    for name, column in COLUMNS.items():
        if name not in existing:
            op.add_column("defect", column)
    indexes = {index["name"] for index in inspector.get_indexes("defect")}
    if "ix_defect_aiqe_run_id" not in indexes:
        op.create_index("ix_defect_aiqe_run_id", "defect", ["aiqe_run_id"])


def downgrade() -> None:
    op.drop_index("ix_defect_aiqe_run_id", table_name="defect")
    for name in COLUMNS:
        op.drop_column("defect", name)
