"""version_task tables (Batch 216 / B6)

Revision ID: 20260905_version_task_model
Revises: 20260904_aitde_v40_governance
Create Date: 2026-09-05

B6 unified fact source: version_task + execution/defect link tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260905_version_task_model"
down_revision: Union[str, None] = "20260904_aitde_v40_governance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = {
    "version_task": [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(300), nullable=False, server_default=""),
        sa.Column("version", sa.String(80), nullable=False, server_default="", index=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual", index=True),
        sa.Column("source_mission_id", sa.Integer(), nullable=True, index=True),
        sa.Column("source_bundle_id", sa.Integer(), nullable=True, index=True),
        sa.Column("requirement_doc_id", sa.Integer(), nullable=True, index=True),
        sa.Column("release_bundle_id", sa.Integer(), nullable=True, index=True),
        sa.Column("environment_id", sa.Integer(), nullable=True, index=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft", index=True),
        sa.Column("verdict", sa.String(20), nullable=False, server_default="", index=True),
        sa.Column("coverage", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("scope", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("risk", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("qa_owner_id", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ],
    "version_task_execution": [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("execution_type", sa.String(30), nullable=False, server_default="runner", index=True),
        sa.Column("execution_id", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("ref", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ],
    "version_task_defect": [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("defect_id", sa.Integer(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ],
}

_INDEXES = [
    ("version_task", "ix_version_task_project_status", ["project_id", "status"]),
    ("version_task_execution", "ix_version_task_execution_task", ["task_id"]),
    ("version_task_defect", "ix_version_task_defect_task", ["task_id"]),
    ("version_task_defect", "ix_version_task_defect_defect", ["defect_id"]),
]

_ORDER = ("version_task", "version_task_execution", "version_task_defect")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for table in _ORDER:
        if table in existing:
            continue
        op.create_table(table, *_TABLES[table])
        for t, index, columns in _INDEXES:
            if t == table:
                op.create_index(index, table, columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in reversed(_ORDER):
        if table in tables:
            op.drop_table(table)
