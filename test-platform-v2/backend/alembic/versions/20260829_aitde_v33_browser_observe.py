"""aitde v3.3 browser_sessions + browser_observation_events

Revision ID: 20260829_aitde_v33_browser
Revises: 20260829_aitde_v33_command_plans
Create Date: 2026-08-29 18:20:00

AITDE V3.3 (V33-006): Browser observe sessions and their standardized
observation events (navigation/click/input/xhr/dom/screenshot/console).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v33_browser"
down_revision: Union[str, None] = "20260829_aitde_v33_command_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "browser_sessions" not in inspector.get_table_names():
        op.create_table(
            "browser_sessions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("mission_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("run_id", sa.Integer, nullable=True),
            sa.Column("environment_id", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("mode", sa.String(16), nullable=False, server_default=sa.text("'OBSERVE'"), index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'")),
            sa.Column("browser_type", sa.String(16), nullable=False, server_default=sa.text("'chromium'")),
            sa.Column("context_ref", sa.String(255), nullable=False, server_default=sa.text("''")),
            sa.Column("started_by", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("started_at", sa.DateTime, nullable=True),
            sa.Column("finished_at", sa.DateTime, nullable=True),
        )

    if "browser_observation_events" not in inspector.get_table_names():
        op.create_table(
            "browser_observation_events",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("browser_session_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("sequence", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("event_type", sa.String(16), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("semantic_target_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("payload_ref_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("timestamp", sa.DateTime, nullable=True),
            sa.UniqueConstraint("browser_session_id", "sequence", name="uq_observation_sequence"),
        )


def downgrade() -> None:
    op.drop_table("browser_observation_events")
    op.drop_table("browser_sessions")
