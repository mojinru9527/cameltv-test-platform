"""Lanhu evidence quality gate + recovery state.

Revision ID: 20260714_lanhu_evidence_quality
Revises: 20260713_lanhu_evidence_pack
Create Date: 2026-07-14

P0-A/B: 为证据包任务/页面新增质量门禁与恢复所需字段：
  job:  parent_job_id, attempt_no, requested_options_json, import_result_json, heartbeat_at
  page: capture_truncated, review_status, reviewer_id, review_comment, reviewed_at
并建立 (status, heartbeat_at) 与 (job_id, review_status) 复合索引。

非破坏、幂等：AUTO_CREATE_TABLES=true 环境下 create_all 已建表但未建列时可安全补齐。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_lanhu_evidence_quality"
down_revision: Union[str, None] = "20260713_lanhu_evidence_pack"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    return column in [c["name"] for c in insp.get_columns(table)]


def _index_exists(conn, table: str, index: str) -> bool:
    insp = sa.inspect(conn)
    return index in [i["name"] for i in insp.get_indexes(table)]


_JOB_COLUMNS = [
    ("parent_job_id", sa.Column("parent_job_id", sa.Integer(), nullable=True)),
    ("attempt_no", sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1")),
    ("requested_options_json", sa.Column("requested_options_json", sa.Text(), nullable=False, server_default="{}")),
    ("import_result_json", sa.Column("import_result_json", sa.Text(), nullable=False, server_default="{}")),
    ("heartbeat_at", sa.Column("heartbeat_at", sa.DateTime(), nullable=True)),
]

_PAGE_COLUMNS = [
    ("capture_truncated", sa.Column("capture_truncated", sa.Boolean(), nullable=False, server_default=sa.false())),
    ("review_status", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending")),
    ("reviewer_id", sa.Column("reviewer_id", sa.Integer(), nullable=False, server_default="0")),
    ("review_comment", sa.Column("review_comment", sa.Text(), nullable=False, server_default="")),
    ("reviewed_at", sa.Column("reviewed_at", sa.DateTime(), nullable=True)),
]


def upgrade() -> None:
    conn = op.get_bind()

    for name, col in _JOB_COLUMNS:
        if not _column_exists(conn, "lanhu_evidence_job", name):
            op.add_column("lanhu_evidence_job", col)
    for name, col in _PAGE_COLUMNS:
        if not _column_exists(conn, "lanhu_evidence_page", name):
            op.add_column("lanhu_evidence_page", col)

    if not _index_exists(conn, "lanhu_evidence_job", "ix_lanhu_evidence_job_parent_job_id"):
        op.create_index("ix_lanhu_evidence_job_parent_job_id", "lanhu_evidence_job", ["parent_job_id"])
    if not _index_exists(conn, "lanhu_evidence_job", "ix_lanhu_evidence_job_heartbeat_at"):
        op.create_index("ix_lanhu_evidence_job_heartbeat_at", "lanhu_evidence_job", ["heartbeat_at"])
    if not _index_exists(conn, "lanhu_evidence_job", "ix_lanhu_evidence_job_status_heartbeat"):
        op.create_index("ix_lanhu_evidence_job_status_heartbeat", "lanhu_evidence_job", ["status", "heartbeat_at"])
    if not _index_exists(conn, "lanhu_evidence_page", "ix_lanhu_evidence_page_review_status"):
        op.create_index("ix_lanhu_evidence_page_review_status", "lanhu_evidence_page", ["review_status"])
    if not _index_exists(conn, "lanhu_evidence_page", "ix_lanhu_evidence_page_job_review"):
        op.create_index("ix_lanhu_evidence_page_job_review", "lanhu_evidence_page", ["job_id", "review_status"])


def downgrade() -> None:
    conn = op.get_bind()

    for idx, table in [
        ("ix_lanhu_evidence_page_job_review", "lanhu_evidence_page"),
        ("ix_lanhu_evidence_page_review_status", "lanhu_evidence_page"),
        ("ix_lanhu_evidence_job_status_heartbeat", "lanhu_evidence_job"),
        ("ix_lanhu_evidence_job_heartbeat_at", "lanhu_evidence_job"),
        ("ix_lanhu_evidence_job_parent_job_id", "lanhu_evidence_job"),
    ]:
        if _index_exists(conn, table, idx):
            op.drop_index(idx, table_name=table)

    for name, _ in reversed(_PAGE_COLUMNS):
        if _column_exists(conn, "lanhu_evidence_page", name):
            op.drop_column("lanhu_evidence_page", name)
    for name, _ in reversed(_JOB_COLUMNS):
        if _column_exists(conn, "lanhu_evidence_job", name):
            op.drop_column("lanhu_evidence_job", name)
