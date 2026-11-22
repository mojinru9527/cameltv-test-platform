"""V16-010: learning candidate gate/approval/publish fields

Revision ID: 20261119_v16_010_learning_gate
Revises: 20261119_v16_008_scope
Create Date: 2026-11-19 22:55:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_010_learning_gate"
down_revision: Union[str, None] = "20261119_v16_008_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS: tuple[tuple[str, sa.types.TypeEngine, dict], ...] = (
    ("benchmark_run_id", sa.String(length=36), {"nullable": True}),
    ("dataset_checksum", sa.String(length=64), {"nullable": False, "server_default": ""}),
    ("baseline_version", sa.String(length=80), {"nullable": False, "server_default": ""}),
    ("gate_policy_version", sa.String(length=32), {"nullable": False, "server_default": ""}),
    ("gate_decision", sa.String(length=16), {"nullable": False, "server_default": ""}),
    ("gate_reasons_json", sa.JSON(), {"nullable": True}),
    ("evaluation_snapshot_json", sa.JSON(), {"nullable": True}),
    ("rule_hash", sa.String(length=64), {"nullable": False, "server_default": ""}),
    ("created_by", sa.Integer(), {"nullable": True}),
    ("approved_by", sa.Integer(), {"nullable": True}),
    ("approved_at", sa.DateTime(timezone=True), {"nullable": True}),
    ("approval_reason", sa.String(length=500), {"nullable": False, "server_default": ""}),
    ("published_at", sa.DateTime(timezone=True), {"nullable": True}),
    ("revoked_at", sa.DateTime(timezone=True), {"nullable": True}),
)


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def upgrade() -> None:
    existing = _columns("learning_candidates")
    if not existing:
        return
    for name, column_type, kwargs in COLUMNS:
        if name not in existing:
            op.add_column("learning_candidates", sa.Column(name, column_type, **kwargs))
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("learning_candidates")}
    if "ix_learning_candidates_benchmark_run_id" not in indexes:
        op.create_index(
            "ix_learning_candidates_benchmark_run_id",
            "learning_candidates",
            ["benchmark_run_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "learning_candidates" not in inspector.get_table_names():
        return
    for index in inspector.get_indexes("learning_candidates"):
        if str(index.get("name")) == "ix_learning_candidates_benchmark_run_id":
            op.drop_index(index["name"], table_name="learning_candidates")
    columns = _columns("learning_candidates")
    for name, _type, _kwargs in COLUMNS:
        if name in columns:
            op.drop_column("learning_candidates", name)
