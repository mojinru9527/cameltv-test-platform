"""aitde v3.1 M31-2: execution_runs + execution_steps + assertion_results

Revision ID: 20260829_aitde_v31_m31_2
Revises: 20260829_aitde_v31_m31_1
Create Date: 2026-08-29 00:45:00

AITDE V3.1 (V31-002): unified execution run + step timeline + oracle assertion
results. ``execution_runs.runtime_status`` is scheduler state, kept separate from
``outcome`` (the frozen business conclusion enum).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v31_m31_2"
down_revision: Union[str, None] = "20260829_aitde_v31_m31_1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "execution_runs" not in inspector.get_table_names():
        op.create_table(
            "execution_runs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("contract_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("adapter_id", sa.Integer, nullable=True),
            sa.Column("environment_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("environment_snapshot_id", sa.Integer, nullable=True, index=True),
            sa.Column("runtime_status", sa.String(16), nullable=False, server_default=sa.text("'QUEUED'"), index=True),
            sa.Column("outcome", sa.String(32), nullable=True, index=True),
            sa.Column("evidence_status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("trigger_type", sa.String(16), nullable=False, server_default=sa.text("'MANUAL'")),
            sa.Column("parent_run_id", sa.Integer, nullable=True),
            sa.Column("retry_no", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
            sa.Column("duration_ms", sa.Integer, nullable=True),
            sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime, nullable=True, index=True),
        )

    if "execution_steps" not in inspector.get_table_names():
        op.create_table(
            "execution_steps",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("sequence", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("step_key", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("step_type", sa.String(16), nullable=False, server_default=sa.text("'ACTION'"), index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("error_type", sa.String(64), nullable=True),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column("input_snapshot_json", sa.Text, nullable=True),
            sa.Column("output_snapshot_json", sa.Text, nullable=True),
            sa.Column("trace_id", sa.String(128), nullable=True),
            sa.Column("span_id", sa.String(128), nullable=True),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
            # SQLite has no ALTER ADD CONSTRAINT: define UNIQUE inline at CREATE TABLE.
            sa.UniqueConstraint("run_id", "sequence", name="uq_run_step_sequence"),
        )

    if "assertion_results" not in inspector.get_table_names():
        op.create_table(
            "assertion_results",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("step_id", sa.Integer, nullable=True),
            sa.Column("oracle_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("oracle_snapshot_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("expected_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("actual_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("result", sa.String(16), nullable=False, server_default=sa.text("'NOT_EVALUATED'"), index=True),
            sa.Column("reason_code", sa.String(64), nullable=False, server_default=sa.text("''")),
            sa.Column("evidence_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("evaluated_at", sa.DateTime, nullable=True),
        )


def downgrade() -> None:
    op.drop_table("assertion_results")
    op.drop_table("execution_steps")
    op.drop_table("execution_runs")
