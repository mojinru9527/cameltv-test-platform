"""aitde v3.4 durable runtime tables (worker / workflow / idempotency / policy / secret / approval)

Revision ID: 20260830_aitde_v34_temporal
Revises: 20260829_aitde_v33_ui_binding
Create Date: 2026-08-30 09:10:00

AITDE V3.4 (plan §3): seed the Durable Runtime data model for Temporal +
Network Worker + Security Plane. All columns use String-valued enums so they
stay stable across SQLite/PostgreSQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260830_aitde_v34_temporal"
down_revision: Union[str, None] = "20260829_aitde_v33_ui_binding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "worker_nodes" not in inspector.get_table_names():
        op.create_table(
            "worker_nodes",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("worker_key", sa.String(64), nullable=False, unique=True, index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("network_zone", sa.String(16), nullable=False, server_default=sa.text("'TEST'"), index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'OFFLINE'"), index=True),
            sa.Column("version", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("machine_identity", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("tags_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("last_heartbeat_at", sa.DateTime, nullable=True),
            sa.Column("registered_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "worker_capabilities" not in inspector.get_table_names():
        op.create_table(
            "worker_capabilities",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("worker_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("capability", sa.String(16), nullable=False, server_default=sa.text("'HTTP'"), index=True),
            sa.Column("version", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("config_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.UniqueConstraint("worker_id", "capability", name="uq_worker_capability"),
        )

    if "workflow_runs" not in inspector.get_table_names():
        op.create_table(
            "workflow_runs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("run_id", sa.Integer, nullable=True, index=True),
            sa.Column("workflow_type", sa.String(32), nullable=False, server_default=sa.text("'SCENARIO_EXECUTION'"), index=True),
            sa.Column("temporal_namespace", sa.String(64), nullable=False, server_default=sa.text("'default'")),
            sa.Column("temporal_workflow_id", sa.String(128), nullable=False, unique=True, index=True),
            sa.Column("temporal_run_id", sa.String(128), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'SCHEDULED'"), index=True),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("closed_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "runtime_idempotency_keys" not in inspector.get_table_names():
        op.create_table(
            "runtime_idempotency_keys",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("scope", sa.String(32), nullable=False, server_default=sa.text("'default'"), index=True),
            sa.Column("key_hash", sa.String(64), nullable=False, index=True),
            sa.Column("resource_type", sa.String(16), nullable=False, server_default=sa.text("'ACTIVITY'")),
            sa.Column("resource_id", sa.Integer, nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("expires_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("scope", "key_hash", name="uq_idempotency_scope_key"),
        )

    if "policy_profiles" not in inspector.get_table_names():
        op.create_table(
            "policy_profiles",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=True, index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("policy_type", sa.String(32), nullable=False, server_default=sa.text("'DRIVER_ACTION'"), index=True),
            sa.Column("version", sa.String(32), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("document_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "policy_bindings" not in inspector.get_table_names():
        op.create_table(
            "policy_bindings",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("environment_id", sa.Integer, nullable=True, index=True),
            sa.Column("network_zone", sa.String(16), nullable=False, server_default=sa.text("'TEST'"), index=True),
            sa.Column("policy_profile_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("100")),
        )

    if "secret_refs" not in inspector.get_table_names():
        op.create_table(
            "secret_refs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("provider", sa.String(32), nullable=False, server_default=sa.text("'env'")),
            sa.Column("external_ref", sa.String(256), nullable=False, server_default=sa.text("''")),
            sa.Column("purpose", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("scope_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("rotated_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "approval_requests" not in inspector.get_table_names():
        op.create_table(
            "approval_requests",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("run_id", sa.Integer, nullable=True, index=True),
            sa.Column("action_type", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("request_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("policy_decision", sa.String(16), nullable=False, server_default=sa.text("'REQUIRE_APPROVAL'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("requested_by", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("approved_by", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.Column("resolved_at", sa.DateTime, nullable=True),
        )


def downgrade() -> None:
    for table in (
        "approval_requests",
        "secret_refs",
        "policy_bindings",
        "policy_profiles",
        "runtime_idempotency_keys",
        "workflow_runs",
        "worker_capabilities",
        "worker_nodes",
    ):
        op.drop_table(table)
