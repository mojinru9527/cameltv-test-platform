"""aitde v3.6 production evidence & real-world data template tables

Revision ID: 20260831_aitde_v36_prodev
Revises: 20260830_aitde_v35_continuous
Create Date: 2026-08-31 09:00:00

AITDE V3.6 (plan §2): seed Production Evidence & Real-World Data Template data
model. 所有协议以 ``只读、可审计、脱敏`` 为核心不变量。枚举列使用 String 值
以保持跨 SQLite/PostgreSQL 稳定；JSON 结构以 Text 存储。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_aitde_v36_prodev"
down_revision: Union[str, None] = "20260830_aitde_v35_continuous"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "production_observation_sessions" not in inspector.get_table_names():
        op.create_table(
            "production_observation_sessions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("worker_id", sa.Integer, nullable=True, index=True),
            sa.Column("mode", sa.String(32), nullable=False, server_default=sa.text("'OBSERVE'"), index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("policy_version", sa.String(32), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("started_by", sa.Integer, nullable=True),
            sa.Column("started_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
        )

    if "observed_journeys" not in inspector.get_table_names():
        op.create_table(
            "observed_journeys",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("session_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("journey_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("summary_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("source_ref_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "observed_journey_steps" not in inspector.get_table_names():
        op.create_table(
            "observed_journey_steps",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("journey_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("sequence", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("event_type", sa.String(32), nullable=False, server_default=sa.text("'NAVIGATE'")),
            sa.Column("semantic_action_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("url_template", sa.String(512), nullable=False, server_default=sa.text("''")),
            sa.Column("xhr_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("evidence_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "production_query_audits" not in inspector.get_table_names():
        op.create_table(
            "production_query_audits",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("session_id", sa.Integer, nullable=True, index=True),
            sa.Column("data_source_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("query_fingerprint", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("operation_type", sa.String(16), nullable=False, server_default=sa.text("'SELECT'"), index=True),
            sa.Column("schema_name", sa.String(64), nullable=True),
            sa.Column("table_names_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("row_count", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("duration_ms", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("policy_decision", sa.String(16), nullable=False, server_default=sa.text("'ALLOW'"), index=True),
            sa.Column("executed_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "masking_profiles" not in inspector.get_table_names():
        op.create_table(
            "masking_profiles",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("version", sa.String(32), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "masking_rules" not in inspector.get_table_names():
        op.create_table(
            "masking_rules",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("profile_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("entity_pattern", sa.String(128), nullable=False, server_default=sa.text("'*'")),
            sa.Column("field_pattern", sa.String(128), nullable=False, server_default=sa.text("'*'"), index=True),
            sa.Column("classification", sa.String(32), nullable=False, server_default=sa.text("'PII'")),
            sa.Column("strategy", sa.String(16), nullable=False, server_default=sa.text("'HASH'"), index=True),
            sa.Column("config_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        )

    if "entity_graph_snapshots" not in inspector.get_table_names():
        op.create_table(
            "entity_graph_snapshots",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("source_environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("root_entity_type", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("root_ref_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("graph_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "prod_data_templates" not in inspector.get_table_names():
        op.create_table(
            "prod_data_templates",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("entity_graph_snapshot_id", sa.Integer, nullable=True, index=True),
            sa.Column("masking_profile_id", sa.Integer, nullable=True, index=True),
            sa.Column("template_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("validation_status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("created_by", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "template_materializations" not in inspector.get_table_names():
        op.create_table(
            "template_materializations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("template_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("target_environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("fixture_id", sa.Integer, nullable=True, index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("id_remap_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )


def downgrade() -> None:
    for table in (
        "template_materializations",
        "prod_data_templates",
        "entity_graph_snapshots",
        "masking_rules",
        "masking_profiles",
        "production_query_audits",
        "observed_journey_steps",
        "observed_journeys",
        "production_observation_sessions",
    ):
        op.drop_table(table)
