"""V16-015: capability verification evidence fields

Revision ID: 20261119_v16_015_capability
Revises: 20261119_v16_019_tool_audit
Create Date: 2026-11-19 23:59:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_v16_015_capability"
down_revision: Union[str, None] = "20261119_v16_019_tool_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = (
    ("verification_run_id", sa.String(length=36), {"nullable": True}),
    ("verification_artifact_refs_json", sa.JSON(), {"nullable": True}),
    ("runner_image_digest", sa.String(length=128), {"nullable": False, "server_default": ""}),
    ("os_version", sa.String(length=80), {"nullable": False, "server_default": ""}),
    ("browser_version", sa.String(length=80), {"nullable": False, "server_default": ""}),
    ("device_id", sa.String(length=120), {"nullable": False, "server_default": ""}),
    ("device_model", sa.String(length=120), {"nullable": False, "server_default": ""}),
    ("device_os", sa.String(length=80), {"nullable": False, "server_default": ""}),
    ("supported_actions_json", sa.JSON(), {"nullable": True}),
    ("limitations_json", sa.JSON(), {"nullable": True}),
)


def _columns(table: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return []
    return [column["name"] for column in inspector.get_columns(table)]


def upgrade() -> None:
    existing = _columns("node_capability_manifests")
    if not existing:
        return
    for name, column_type, kwargs in COLUMNS:
        if name not in existing:
            op.add_column("node_capability_manifests", sa.Column(name, column_type, **kwargs))
    indexes = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes("node_capability_manifests")
    }
    if "ix_node_capability_manifests_verification_run_id" not in indexes:
        op.create_index(
            "ix_node_capability_manifests_verification_run_id",
            "node_capability_manifests",
            ["verification_run_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "node_capability_manifests" not in inspector.get_table_names():
        return
    for index in inspector.get_indexes("node_capability_manifests"):
        if str(index.get("name")) == "ix_node_capability_manifests_verification_run_id":
            op.drop_index(index["name"], table_name="node_capability_manifests")
    columns = _columns("node_capability_manifests")
    for name, _type, _kwargs in COLUMNS:
        if name in columns:
            op.drop_column("node_capability_manifests", name)
