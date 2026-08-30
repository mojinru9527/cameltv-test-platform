"""aitde v3.7 smart regression tables (lineage / change set / impact / selection)

Revision ID: 20260901_aitde_v37_smartreg
Revises: 20260831_aitde_v36_prodev
Create Date: 2026-09-01 09:00:00

AITDE V3.7 (plan §§2-6): Impact Analysis + Smart Regression data model. All
columns use String-valued enums so they stay stable across SQLite/PostgreSQL.
Guards on table existence so a re-run (stamp/rollback + upgrade) is idempotent.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260901_aitde_v37_smartreg"
down_revision: Union[str, None] = "20260831_aitde_v36_prodev"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "lineage_edges" not in inspector.get_table_names():
        op.create_table(
            "lineage_edges",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=True, index=True),
            sa.Column("from_type", sa.String(32), nullable=False, index=True),
            sa.Column("from_id", sa.Integer, nullable=False, index=True),
            sa.Column("to_type", sa.String(32), nullable=False, index=True),
            sa.Column("to_id", sa.Integer, nullable=False, index=True),
            sa.Column("edge_type", sa.String(32), nullable=False, index=True),
            sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("1.0")),
            sa.Column("created_by_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.UniqueConstraint("project_id", "from_type", "from_id", "to_type", "to_id", "edge_type", name="uq_lineage_edge"),
        )

    if "change_sets" not in inspector.get_table_names():
        op.create_table(
            "change_sets",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("change_type", sa.String(32), nullable=False, server_default=sa.text("'PRD'"), index=True),
            sa.Column("source_from_ref", sa.Text, nullable=True),
            sa.Column("source_to_ref", sa.Text, nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'DETECTED'"), index=True),
            sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "change_items" not in inspector.get_table_names():
        op.create_table(
            "change_items",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("change_set_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("change_kind", sa.String(16), nullable=False, server_default=sa.text("'CHANGED'"), index=True),
            sa.Column("entity_type", sa.String(32), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("entity_key", sa.String(255), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("before_json", sa.Text, nullable=True),
            sa.Column("after_json", sa.Text, nullable=True),
            sa.Column("risk_hint", sa.String(32), nullable=False, server_default=sa.text("'NONE'"), index=True),
            sa.Column("source_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
        )

    if "impact_analysis_runs" not in inspector.get_table_names():
        op.create_table(
            "impact_analysis_runs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("change_set_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("algorithm_version", sa.String(16), nullable=False, server_default=sa.text("'v1'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("input_hash", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
        )

    if "impact_results" not in inspector.get_table_names():
        op.create_table(
            "impact_results",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("impact_run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("impact_score", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("risk_level", sa.String(4), nullable=False, server_default=sa.text("'P2'"), index=True),
            sa.Column("reasons_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("path_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("decision", sa.String(16), nullable=False, server_default=sa.text("'INCLUDE'"), index=True),
        )

    if "regression_selections" not in inspector.get_table_names():
        op.create_table(
            "regression_selections",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("impact_run_id", sa.Integer, nullable=True, index=True),
            sa.Column("build_observation_id", sa.Integer, nullable=True, index=True),
            sa.Column("selection_type", sa.String(16), nullable=False, server_default=sa.text("'SMART'"), index=True),
            sa.Column("selected_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("excluded_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("fallback_reason", sa.Text, nullable=True),
            sa.Column("content_hash", sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
        )

    if "regression_selection_items" not in inspector.get_table_names():
        op.create_table(
            "regression_selection_items",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("selection_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("decision", sa.String(16), nullable=False, server_default=sa.text("'SELECTED'"), index=True),
            sa.Column("reason", sa.Text, nullable=False, server_default=sa.text("''")),
            sa.Column("source", sa.String(32), nullable=False, server_default=sa.text("'SYSTEM'")),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), index=True),
            sa.UniqueConstraint("selection_id", "scenario_version_id", name="uq_reg_sel_item"),
        )


def downgrade() -> None:
    for table in (
        "regression_selection_items",
        "regression_selections",
        "impact_results",
        "impact_analysis_runs",
        "change_items",
        "change_sets",
        "lineage_edges",
    ):
        op.drop_table(table)
