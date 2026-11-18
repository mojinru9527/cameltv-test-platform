"""AUD-013：agent_executions 增加可追溯字段（版本/模型/hash/tool calls）

Revision ID: 20261124_aud013_agent_protocol
Revises: 20261124_aud012_defect_draft
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud013_agent_protocol"
down_revision = "20261124_aud012_defect_draft"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("agent_version", sa.String(length=40)),
    ("prompt_version", sa.String(length=80)),
    ("model_provider", sa.String(length=80)),
    ("model_name", sa.String(length=120)),
    ("input_hash", sa.String(length=80)),
    ("output_hash", sa.String(length=80)),
    ("token_usage_json", sa.JSON()),
    ("source_refs_json", sa.JSON()),
    ("tool_calls_json", sa.JSON()),
    ("warnings_json", sa.JSON()),
    ("needs_human", sa.Boolean()),
    ("task_id", sa.String(length=80)),
    ("parent_task_id", sa.String(length=80)),
    ("idempotency_key", sa.String(length=128)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_executions" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("agent_executions")}
    for name, type_ in _COLUMNS:
        if name in existing:
            continue
        op.add_column("agent_executions", sa.Column(name, type_, nullable=True))
    op.execute(
        "UPDATE agent_executions SET agent_version = '1.0.0' WHERE agent_version IS NULL"
    )
    op.execute("UPDATE agent_executions SET needs_human = 0 WHERE needs_human IS NULL")
    indexes = {index["name"] for index in inspector.get_indexes("agent_executions")}
    for index, columns in (
        ("ix_agent_executions_task_id", ["task_id"]),
        ("ix_agent_executions_idempotency_key", ["idempotency_key"]),
    ):
        if index not in indexes:
            op.create_index(index, "agent_executions", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_executions" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("agent_executions")}
    for index in ("ix_agent_executions_idempotency_key", "ix_agent_executions_task_id"):
        if index in indexes:
            op.drop_index(index, table_name="agent_executions")
    existing = {column["name"] for column in inspector.get_columns("agent_executions")}
    for name, _type in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("agent_executions", name)
