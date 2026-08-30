"""aitde v3.5 continuous acceptance tables (fingerprint / build / campaign / profile / trigger / gate)

Revision ID: 20260830_aitde_v35_continuous
Revises: 20260830_aitde_v34_temporal
Create Date: 2026-08-30 11:00:00

AITDE V3.5 (plan §2): seed Continuous Acceptance data model. All columns use
String-valued enums so they stay stable across SQLite/PostgreSQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260830_aitde_v35_continuous"
down_revision: Union[str, None] = "20260830_aitde_v34_temporal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "environment_fingerprints" not in inspector.get_table_names():
        op.create_table(
            "environment_fingerprints",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("fingerprint_hash", sa.String(64), nullable=False, index=True),
            sa.Column("build_label", sa.String(128), nullable=True),
            sa.Column("components_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("source_type", sa.String(16), nullable=False, server_default=sa.text("'AUTO'"), index=True),
            sa.Column("captured_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.UniqueConstraint("environment_id", "fingerprint_hash", name="uq_env_fingerprint_hash"),
        )

    if "build_observations" not in inspector.get_table_names():
        op.create_table(
            "build_observations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("fingerprint_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("previous_fingerprint_id", sa.Integer, nullable=True),
            sa.Column("change_summary_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("detected_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'NEW'"), index=True),
        )

    if "execution_campaigns" not in inspector.get_table_names():
        op.create_table(
            "execution_campaigns",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("campaign_type", sa.String(32), nullable=False, server_default=sa.text("'IMPACTED'"), index=True),
            sa.Column("environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("build_observation_id", sa.Integer, nullable=True, index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'DRAFT'"), index=True),
            sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'AUTO'")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "run_profiles" not in inspector.get_table_names():
        op.create_table(
            "run_profiles",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("selector_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("evidence_policy_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("retry_policy_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("parallelism", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
        )

    if "campaign_scenarios" not in inspector.get_table_names():
        op.create_table(
            "campaign_scenarios",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("campaign_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("selection_reason_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("required", sa.String(16), nullable=False, server_default=sa.text("'REQUIRED'"), index=True),
            sa.Column("run_id", sa.Integer, nullable=True, index=True),
            sa.UniqueConstraint("campaign_id", "scenario_version_id", name="uq_campaign_scenario"),
        )

    if "triggers" not in inspector.get_table_names():
        op.create_table(
            "triggers",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("trigger_type", sa.String(16), nullable=False, server_default=sa.text("'MANUAL'"), index=True),
            sa.Column("config_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("last_fired_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "quality_gate_policies" not in inspector.get_table_names():
        op.create_table(
            "quality_gate_policies",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("name", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("version", sa.String(32), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("policy_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "quality_gate_results" not in inspector.get_table_names():
        op.create_table(
            "quality_gate_results",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("campaign_id", sa.Integer, nullable=True, index=True),
            sa.Column("build_observation_id", sa.Integer, nullable=True, index=True),
            sa.Column("policy_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("result", sa.String(16), nullable=False, server_default=sa.text("'INCONCLUSIVE'"), index=True),
            sa.Column("checks_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("evaluated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.Column("override_status", sa.String(16), nullable=True),
            sa.Column("override_by", sa.Integer, nullable=True),
            sa.Column("override_reason", sa.Text, nullable=True),
        )


def downgrade() -> None:
    for table in (
        "quality_gate_results",
        "quality_gate_policies",
        "triggers",
        "campaign_scenarios",
        "run_profiles",
        "execution_campaigns",
        "build_observations",
        "environment_fingerprints",
    ):
        op.drop_table(table)
