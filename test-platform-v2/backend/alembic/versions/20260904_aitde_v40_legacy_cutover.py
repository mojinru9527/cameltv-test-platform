"""aitde v4.0 legacy cutover: inventory + mapping/cutover tables

Revision ID: 20260904_aitde_v40_legacy_cutover
Revises: 20260903_aitde_v39_reality_r3_fingerprint
Create Date: 2026-09-04 01:00:00

V4.0 (V40-001/002) migration. Creates:

* ``legacy_usage_records``   — V40-001 observed usage of v1 endpoints/pages/jobs.
* ``legacy_object_mappings`` — V40-002 legacy -> canonical mapping, unique per
  (legacy_type, legacy_id) so it is idempotent.
* ``cutover_batches``        — V40-002 idempotent cutover batch orchestration.

Indexes are created explicitly (create_index / drop_index) so the migration is
reversible for the §77-78 PostgreSQL previous-head <-> current-head drill — a
batched ``drop_column``/``drop_table`` otherwise leaves orphan indexes that break
a re-upgrade.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260904_aitde_v40_legacy_cutover"
down_revision: Union[str, None] = "20260903_aitde_v39_reality_r3_fingerprint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> dict:
    return {
        "legacy_usage_records": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("consumer_type", sa.String(16), nullable=False, server_default="UNKNOWN"),
            sa.Column("surface_kind", sa.String(16), nullable=False, server_default="ENDPOINT"),
            sa.Column("path", sa.String(255), nullable=False, server_default=""),
            sa.Column("method", sa.String(16), nullable=False, server_default=""),
            sa.Column("object_type", sa.String(32), nullable=False, server_default="TEST_CASE"),
            sa.Column("object_id", sa.Integer(), nullable=True),
            sa.Column("owner", sa.String(64), nullable=False, server_default=""),
            sa.Column("traffic_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("replacement_v2", sa.String(255), nullable=False, server_default=""),
            sa.Column("deprecation_stage", sa.String(16), nullable=False, server_default="ACTIVE"),
            sa.Column("sunset_date", sa.String(32), nullable=True),
            sa.Column("rollback_switch", sa.String(64), nullable=False, server_default=""),
            sa.Column("first_seen_at", sa.DateTime(), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        ],
        "legacy_object_mappings": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("legacy_type", sa.String(32), nullable=False, server_default="TEST_CASE"),
            sa.Column("legacy_id", sa.Integer(), nullable=False),
            sa.Column("canonical_type", sa.String(32), nullable=False, server_default=""),
            sa.Column("canonical_id", sa.Integer(), nullable=False),
            sa.Column("migration_status", sa.String(16), nullable=False, server_default="PENDING"),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("legacy_type", "legacy_id", name="uq_legacy_object_mapping"),
        ],
        "cutover_batches": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("batch_key", sa.String(64), nullable=False, server_default=""),
            sa.Column("object_type", sa.String(32), nullable=False, server_default="TEST_CASE"),
            sa.Column("criteria_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
            sa.Column("planned_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("migrated_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verification_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        ],
    }


_INDEXES = [
    # (table, index, columns)
    ("legacy_usage_records", "ix_legacy_usage_project", ["project_id"]),
    ("legacy_usage_records", "ix_legacy_usage_object_type", ["object_type"]),
    ("legacy_usage_records", "ix_legacy_usage_deprecation_stage", ["deprecation_stage"]),
    ("legacy_usage_records", "ix_legacy_usage_path", ["path"]),
    ("legacy_usage_records", "ix_legacy_usage_consumer", ["consumer_type"]),
    ("legacy_object_mappings", "ix_legacy_map_project", ["project_id"]),
    ("legacy_object_mappings", "ix_legacy_map_legacy_type", ["legacy_type"]),
    ("legacy_object_mappings", "ix_legacy_map_legacy_id", ["legacy_id"]),
    ("legacy_object_mappings", "ix_legacy_map_status", ["migration_status"]),
    ("cutover_batches", "ix_cutover_batch_key", ["batch_key"]),
    ("cutover_batches", "ix_cutover_batch_object_type", ["object_type"]),
    ("cutover_batches", "ix_cutover_batch_status", ["status"]),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for table, columns in _tables().items():
        if table in existing:
            continue
        op.create_table(table, *columns)
    for table, index, columns in _INDEXES:
        if table not in existing:
            op.create_index(index, table, columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table, index, columns in reversed(_INDEXES):
        if table in tables:
            existing_idx = {i["name"] for i in inspector.get_indexes(table)}
            if index in existing_idx:
                op.drop_index(index, table_name=table)
    for table in reversed(list(_tables().keys())):
        if table in tables:
            op.drop_table(table)
