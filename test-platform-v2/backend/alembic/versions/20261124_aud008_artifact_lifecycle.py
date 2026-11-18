"""AUD-008：run_artifacts 上传生命周期 / 保留期 / 墓碑

Revision ID: 20261124_aud008_artifact_lifecycle
Revises: 20261124_aud007_assertion_fields
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud008_artifact_lifecycle"
down_revision = "20261124_aud007_assertion_fields"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("project_id", sa.Integer()),
    ("expected_sha256", sa.String(length=64)),
    ("upload_status", sa.String(length=20)),
    ("retention_until", sa.DateTime(timezone=True)),
    ("deleted_at", sa.DateTime(timezone=True)),
    ("access_scope", sa.String(length=16)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "run_artifacts" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("run_artifacts")}
    for name, type_ in _COLUMNS:
        if name in existing:
            continue
        op.add_column("run_artifacts", sa.Column(name, type_, nullable=True))
    # 既有行都是已落库证据：回填 AVAILABLE + access_scope，避免被当作"上传未完成"。
    op.execute(
        "UPDATE run_artifacts SET upload_status = 'AVAILABLE' WHERE upload_status IS NULL"
    )
    op.execute(
        "UPDATE run_artifacts SET access_scope = 'project' WHERE access_scope IS NULL"
    )
    op.execute(
        "UPDATE run_artifacts "
        "SET project_id = (SELECT tr.project_id FROM test_runs tr WHERE tr.id = run_artifacts.run_id) "
        "WHERE project_id IS NULL"
    )
    indexes = {index["name"] for index in inspector.get_indexes("run_artifacts")}
    if "ix_run_artifacts_project_id" not in indexes:
        op.create_index("ix_run_artifacts_project_id", "run_artifacts", ["project_id"])
    if "ix_run_artifacts_upload_status" not in indexes:
        op.create_index("ix_run_artifacts_upload_status", "run_artifacts", ["upload_status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "run_artifacts" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("run_artifacts")}
    for index in ("ix_run_artifacts_upload_status", "ix_run_artifacts_project_id"):
        if index in indexes:
            op.drop_index(index, table_name="run_artifacts")
    if bind.dialect.name == "sqlite":
        # SQLite 不支持 DROP COLUMN 于被 FK 引用的列；降级保留这些向后兼容的追加列。
        return
    existing = {column["name"] for column in inspector.get_columns("run_artifacts")}
    for name, _type in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("run_artifacts", name)
