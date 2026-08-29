"""aitde v3.1 M31-4: shadow_audit_feedback

Revision ID: 20260829_aitde_v31_m31_4
Revises: 20260829_aitde_v31_m31_3
Create Date: 2026-08-29 01:20:00

AITDE V3.1 (V31-015): tester deep-audit feedback (CONFIRMED / FALSE_PASS /
FALSE_FAIL). Append-only; never mutates a Run's historical outcome.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_aitde_v31_m31_4"
down_revision: Union[str, None] = "20260829_aitde_v31_m31_3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "shadow_audit_feedback" not in inspector.get_table_names():
        op.create_table(
            "shadow_audit_feedback",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("run_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("audit_outcome", sa.String(16), nullable=False, server_default=sa.text("''"), index=True),
            sa.Column("reason", sa.Text, nullable=False, server_default=sa.text("''")),
            sa.Column("created_by", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime, nullable=True, index=True),
        )


def downgrade() -> None:
    op.drop_table("shadow_audit_feedback")
