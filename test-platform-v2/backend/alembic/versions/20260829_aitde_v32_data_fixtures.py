"""aitde v3.2 fixture/lease/snapshot/cleanup/legacy tables

Revision ID: 20260829_aitde_v32_data_fixtures
Revises: 20260829_aitde_v32_data_plans
Create Date: 2026-08-29 03:00:00

AITDE V3.2 (V32-009..V32-012, V32-015): fixture (state machine), entities,
leases (concurrency isolation), snapshots (before/after/verify), cleanup records
(idempotent compensation) and legacy dataset links.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v32_data_fixtures"
down_revision: Union[str, None] = "20260829_aitde_v32_data_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "data_fixtures" not in inspector.get_table_names():
        op.create_table(
            "data_fixtures",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("run_id", sa.Integer, nullable=True, index=True),
            sa.Column("data_plan_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("environment_id", sa.Integer, nullable=True),
            sa.Column("data_source_id", sa.Integer, nullable=True, index=True),
            sa.Column("strategy", sa.String(32), nullable=False, server_default=sa.text("'EXISTING'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PROVISIONING'"), index=True),
            sa.Column("namespace", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("manifest_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("expires_at", sa.DateTime, nullable=True),
            sa.Column("cleanup_status", sa.String(16), nullable=False, server_default=sa.text("''")),
        )

    if "fixture_entities" not in inspector.get_table_names():
        op.create_table(
            "fixture_entities",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("fixture_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("entity_type", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("logical_key", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("physical_ref_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_by_fixture", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("before_snapshot_ref", sa.String(255), nullable=True),
            sa.Column("after_snapshot_ref", sa.String(255), nullable=True),
            sa.Column("cleanup_action_json", sa.Text, nullable=True),
        )

    if "fixture_leases" not in inspector.get_table_names():
        op.create_table(
            "fixture_leases",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("fixture_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("lease_token", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("leased_at", sa.DateTime, nullable=True),
            sa.Column("expires_at", sa.DateTime, nullable=True),
            sa.Column("released_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("fixture_id", "run_id", name="uq_fixture_lease_run"),
        )

    if "data_snapshots" not in inspector.get_table_names():
        op.create_table(
            "data_snapshots",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("fixture_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("run_id", sa.Integer, nullable=True),
            sa.Column("entity_id", sa.Integer, nullable=True),
            sa.Column("snapshot_type", sa.String(24), nullable=False, server_default=sa.text("'BEFORE'"), index=True),
            sa.Column("storage_uri", sa.String(255), nullable=True),
            sa.Column("snapshot_json", sa.Text, nullable=True),
            sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("created_at", sa.DateTime, nullable=True),
        )

    if "cleanup_records" not in inspector.get_table_names():
        op.create_table(
            "cleanup_records",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("fixture_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("attempt_no", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'RUNNING'"), index=True),
            sa.Column("actions_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("error_json", sa.Text, nullable=True),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("fixture_id", "attempt_no", name="uq_cleanup_fixture_attempt"),
        )

    if "legacy_dataset_links" not in inspector.get_table_names():
        op.create_table(
            "legacy_dataset_links",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("data_source_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("legacy_dataset_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.UniqueConstraint("legacy_dataset_id", name="uq_legacy_dataset_link"),
        )


def downgrade() -> None:
    for table in (
        "legacy_dataset_links",
        "cleanup_records",
        "data_snapshots",
        "fixture_leases",
        "fixture_entities",
        "data_fixtures",
    ):
        op.drop_table(table)
