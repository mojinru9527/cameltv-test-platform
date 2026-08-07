"""batch121_interaction_edge

Revision ID: 20260808_batch121_interaction_edge
Revises: 20260807_batch120_ai_task
Create Date: 2026-08-08

C120-1：交互拓扑边全量入库（3172 边）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260808_batch121_interaction_edge"
down_revision: Union[str, None] = "20260807_batch120_ai_task"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    import sqlalchemy as _sa
    if "interaction_edge" in _sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "interaction_edge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("from_module", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("entry", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("to", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("evidence", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("source_batch", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_interaction_edge_project_id", "interaction_edge", ["project_id"])
    op.create_index("ix_interaction_edge_to", "interaction_edge", ["to"])


def downgrade() -> None:
    bind = op.get_bind()
    import sqlalchemy as _sa
    if "interaction_edge" not in _sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_interaction_edge_project_id", table_name="interaction_edge")
    op.drop_index("ix_interaction_edge_to", table_name="interaction_edge")
    op.drop_table("interaction_edge")
