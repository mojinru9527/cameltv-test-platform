"""aitde v4.0 enterprise governance tables

Revision ID: 20260904_aitde_v40_governance
Revises: 20260904_aitde_v40_legacy_case_migration
Create Date: 2026-09-04 03:00:00

V4.0 (V40-011/012/014/015/017) migration. Creates the enterprise governance
tables:

* ``retention_policies``      — V40-012 artifact retention.
* ``model_policies``          — V40-014 sensitivity -> provider/model routing.
* ``model_usage_ledger``      — V40-015 model/runtime usage + cost accounting.
* ``governance_exceptions``   — V40-011 time-boxed governance exceptions.
* ``dr_test_runs``            — V40-017 DR drill RTO/RPO evidence.

Indexes are created explicitly so the migration is reversible for the §77-78
PostgreSQL previous-head <-> current-head drill.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260904_aitde_v40_governance"
down_revision: Union[str, None] = "20260904_aitde_v40_legacy_case_migration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = {
    "retention_policies": [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("artifact_type", sa.String(16), nullable=False, server_default="EVIDENCE"),
        sa.Column("sensitivity", sa.String(16), nullable=False, server_default="INTERNAL"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("archive_action", sa.String(16), nullable=False, server_default="ARCHIVE"),
        sa.Column("delete_action", sa.String(16), nullable=False, server_default="DELETE"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    ],
    "model_policies": [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("sensitivity_level", sa.String(16), nullable=False, server_default="INTERNAL"),
        sa.Column("allowed_providers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("allowed_models_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("redaction_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("persistence_allowed", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    ],
    "model_usage_ledger": [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mission_id", sa.Integer(), nullable=True),
        sa.Column("operation_type", sa.String(32), nullable=False, server_default=""),
        sa.Column("model_ref", sa.String(128), nullable=False, server_default=""),
        sa.Column("input_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_amount", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    ],
    "governance_exceptions": [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exception_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("target_type", sa.String(32), nullable=False, server_default=""),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    ],
    "dr_test_runs": [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("test_type", sa.String(32), nullable=False, server_default="BACKUP_RESTORE"),
        sa.Column("environment", sa.String(32), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("rto_seconds", sa.Integer(), nullable=True),
        sa.Column("rpo_seconds", sa.Integer(), nullable=True),
        sa.Column("evidence_uri", sa.Text(), nullable=False, server_default=""),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    ],
}

_INDEXES = [
    ("retention_policies", "ix_retention_policy_type", ["artifact_type", "sensitivity"]),
    ("retention_policies", "ix_retention_policy_status", ["status"]),
    ("model_policies", "ix_model_policy_sens", ["sensitivity_level"]),
    ("model_usage_ledger", "ix_model_usage_project", ["project_id"]),
    ("model_usage_ledger", "ix_model_usage_created", ["created_at"]),
    ("governance_exceptions", "ix_gov_exception_status", ["status"]),
    ("dr_test_runs", "ix_dr_test_type", ["test_type"]),
    ("dr_test_runs", "ix_dr_test_status", ["status"]),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for table, cols in _TABLES.items():
        if table in existing:
            continue
        op.create_table(table, *cols)
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
    for table in reversed(list(_TABLES.keys())):
        if table in tables:
            op.drop_table(table)
