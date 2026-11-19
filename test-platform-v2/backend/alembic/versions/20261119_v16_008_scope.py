"""V16-008: regression scope snapshots + mandatory scope binding

Revision ID: 20261119_v16_008_scope
Revises: 20261119_v16_006_outbox
Create Date: 2026-11-19 22:40:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_008_scope"
down_revision: Union[str, None] = "20261119_v16_006_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "aiqe_regression_scopes" not in inspector.get_table_names():
        op.create_table(
            "aiqe_regression_scopes",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("defect_id", sa.Integer(), nullable=False),
            sa.Column("scope", sa.String(length=48), nullable=False),
            sa.Column("rule_version", sa.String(length=32), nullable=False),
            sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("mandatory_refs_json", sa.JSON(), nullable=False),
            sa.Column("mandatory_node_keys_json", sa.JSON(), nullable=False),
            sa.Column("related_node_keys_json", sa.JSON(), nullable=False),
            sa.Column("smoke_node_keys_json", sa.JSON(), nullable=False),
            sa.Column("excluded_json", sa.JSON(), nullable=False),
            sa.Column("reasons_json", sa.JSON(), nullable=False),
            sa.Column("inputs_json", sa.JSON(), nullable=False),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "uq_aiqe_regression_scopes_checksum",
            "aiqe_regression_scopes",
            ["project_id", "defect_id", "checksum_sha256"],
            unique=True,
        )
        op.create_index(
            "ix_aiqe_regression_scopes_project_id", "aiqe_regression_scopes", ["project_id"]
        )
        op.create_index(
            "ix_aiqe_regression_scopes_defect_id", "aiqe_regression_scopes", ["defect_id"]
        )
        op.create_index(
            "ix_aiqe_regression_scopes_checksum_sha256",
            "aiqe_regression_scopes",
            ["checksum_sha256"],
        )
    columns = _columns("defect_regressions")
    if columns and "scope_snapshot_id" not in columns:
        op.add_column(
            "defect_regressions", sa.Column("scope_snapshot_id", sa.String(length=36), nullable=True)
        )
        op.create_index(
            "ix_defect_regressions_scope_snapshot_id",
            "defect_regressions",
            ["scope_snapshot_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "defect_regressions" in inspector.get_table_names():
        for index in inspector.get_indexes("defect_regressions"):
            if str(index.get("name")) == "ix_defect_regressions_scope_snapshot_id":
                op.drop_index(index["name"], table_name="defect_regressions")
        if "scope_snapshot_id" in _columns("defect_regressions"):
            op.drop_column("defect_regressions", "scope_snapshot_id")
    if "aiqe_regression_scopes" in inspector.get_table_names():
        for name in (
            "ix_aiqe_regression_scopes_checksum_sha256",
            "ix_aiqe_regression_scopes_defect_id",
            "ix_aiqe_regression_scopes_project_id",
            "uq_aiqe_regression_scopes_checksum",
        ):
            op.drop_index(name, table_name="aiqe_regression_scopes")
        op.drop_table("aiqe_regression_scopes")
