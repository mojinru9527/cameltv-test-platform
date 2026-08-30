"""aitde v3.8 ai qa closed loop tables (failure hypothesis / flaky / suggestion / gap / feedback / evaluation / strategy)

Revision ID: 20260902_aitde_v38_aiclosed
Revises: 20260901_aitde_v37_smartreg
Create Date: 2026-09-02 09:00:00

AITDE V3.8 (plan §2): AI QA Closed Loop data model. All columns use String-valued
enums so they stay stable across SQLite/PostgreSQL. Guards on table existence so
a re-run (stamp/rollback + upgrade) is idempotent.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_aitde_v38_aiclosed"
down_revision: Union[str, None] = "20260901_aitde_v37_smartreg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "failure_hypotheses" not in inspector.get_table_names():
        op.create_table(
            "failure_hypotheses",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("hypothesis_type", sa.String(48), nullable=False, server_default=sa.text("'UNKNOWN'"), index=True),
            sa.Column("summary", sa.Text, nullable=False, server_default=sa.text("''")),
            sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("evidence_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("suggested_checks_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("model_ref", sa.String(255), nullable=True),
            sa.Column("prompt_version", sa.String(64), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'GENERATED'"), index=True),
            sa.Column("reviewed_by", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "flaky_signals" not in inspector.get_table_names():
        op.create_table(
            "flaky_signals",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("scenario_adapter_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("signal_type", sa.String(32), nullable=False, server_default=sa.text("'INTERMITTENT_ERROR'"), index=True),
            sa.Column("signature", sa.String(255), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("weight", sa.Float, nullable=False, server_default=sa.text("1.0")),
            sa.Column("details_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "flaky_clusters" not in inspector.get_table_names():
        op.create_table(
            "flaky_clusters",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("scenario_adapter_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("cluster_key", sa.String(255), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("classification", sa.String(16), nullable=False, server_default=sa.text("'UNCLASSIFIED'"), index=True),
            sa.Column("sample_size", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("failure_rate", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "ai_suggestions" not in inspector.get_table_names():
        op.create_table(
            "ai_suggestions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("suggestion_type", sa.String(32), nullable=False, server_default=sa.text("'RISK'"), index=True),
            sa.Column("target_type", sa.String(32), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("target_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("payload_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("evidence_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'OPEN'"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "human_feedback" not in inspector.get_table_names():
        op.create_table(
            "human_feedback",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("target_type", sa.String(32), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("target_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("feedback_type", sa.String(16), nullable=False, server_default=sa.text("'CORRECTION'"), index=True),
            sa.Column("before_json", sa.Text, nullable=True),
            sa.Column("after_json", sa.Text, nullable=True),
            sa.Column("reason", sa.Text, nullable=True),
            sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "strategy_performance" not in inspector.get_table_names():
        op.create_table(
            "strategy_performance",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("strategy_type", sa.String(32), nullable=False, server_default=sa.text("'DATA'"), index=True),
            sa.Column("strategy_key", sa.String(128), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("context_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("attempt_count", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("success_count", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("median_duration_ms", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("failure_breakdown_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "scenario_gap_candidates" not in inspector.get_table_names():
        op.create_table(
            "scenario_gap_candidates",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("gap_type", sa.String(32), nullable=False, server_default=sa.text("'PROD_NEW_STATE'"), index=True),
            sa.Column("title", sa.String(255), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("description", sa.Text, nullable=False, server_default=sa.text("''")),
            sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("evidence_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("risk_level", sa.String(4), nullable=False, server_default=sa.text("'P2'"), index=True),
            sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'OPEN'"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "model_evaluation_runs" not in inspector.get_table_names():
        op.create_table(
            "model_evaluation_runs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("evaluation_suite", sa.String(128), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("model_ref", sa.String(255), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("prompt_versions_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("metrics_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("artifact_uri", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )


def downgrade() -> None:
    for table in (
        "model_evaluation_runs",
        "scenario_gap_candidates",
        "strategy_performance",
        "human_feedback",
        "ai_suggestions",
        "flaky_clusters",
        "flaky_signals",
        "failure_hypotheses",
    ):
        op.drop_table(table)
