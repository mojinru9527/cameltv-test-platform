"""Add quality_gate_config table for R3 quality gate feature.

Revision ID: 20260702_0007
Revises: 20260702_0006
Create Date: 2026-07-02

The QualityGateConfig model already exists (models/quality_gate.py) and is fully
functional when AUTO_CREATE_TABLES=true. This migration ensures the table is
created explicitly for production PG deployments.

Columns:
  - id: int PK
  - project_id: int (unique, indexed)
  - pass_rate_threshold: int (default 80)
  - p0_max: int (default 0)
  - p1_max: int (default 5)
  - enabled: bool (default True)
  - created_at / updated_at: datetime
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260702_0007"
down_revision: Union[str, None] = "20260702_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip if table already exists (e.g. created by ORM auto-create)
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "quality_gate_config" in insp.get_table_names():
        return
    op.create_table(
        "quality_gate_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), default=0, unique=True, index=True),
        sa.Column("pass_rate_threshold", sa.Integer(), default=80),
        sa.Column("p0_max", sa.Integer(), default=0),
        sa.Column("p1_max", sa.Integer(), default=5),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("quality_gate_config")
