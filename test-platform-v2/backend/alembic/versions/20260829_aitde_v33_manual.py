"""aitde v3.3 manual_execution_sessions + manual_execution_steps

Revision ID: 20260829_aitde_v33_manual
Revises: 20260829_aitde_v33_browser
Create Date: 2026-08-29 18:40:00

AITDE V3.3 (V33-008): assisted-manual sessions with durable (refresh-surviving)
step state.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v33_manual"
down_revision: Union[str, None] = "20260829_aitde_v33_browser"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "manual_execution_sessions" not in inspector.get_table_names():
        op.create_table(
            "manual_execution_sessions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("browser_session_id", sa.Integer, nullable=True),
            sa.Column("tester_id", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'")),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
        )

    if "manual_execution_steps" not in inspector.get_table_names():
        op.create_table(
            "manual_execution_steps",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("manual_session_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("sequence", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("step_key", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'"), index=True),
            sa.Column("tester_note", sa.Text, nullable=False, server_default=sa.text("''")),
            sa.Column("evidence_refs_json", sa.Text, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("completed_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("manual_session_id", "sequence", name="uq_manual_step_sequence"),
        )


def downgrade() -> None:
    op.drop_table("manual_execution_steps")
    op.drop_table("manual_execution_sessions")
