"""Add report_template table for R4 report template feature.

Revision ID: 20260702_0008
Revises: 20260702_0007
Create Date: 2026-07-02

The report_template table stores per-project report content templates.
Each template defines which sections (stats, cases, defects, gate, trend,
description) to include and their display order.

Columns:
  - id: int PK
  - project_id: int (indexed)
  - name: varchar(100)
  - description: varchar(500)
  - sections: text (JSON array of section definitions)
  - is_default: bool
  - created_at / updated_at: datetime
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260702_0008"
down_revision: Union[str, None] = "20260702_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip if table already exists (e.g. created by ORM auto-create)
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "report_template" in insp.get_table_names():
        return
    op.create_table(
        "report_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), default=0, index=True),
        sa.Column("name", sa.String(100), default=""),
        sa.Column("description", sa.String(500), default=""),
        sa.Column("sections", sa.Text(), default="[]"),
        sa.Column("is_default", sa.Boolean(), default=False),
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
    op.drop_table("report_template")
