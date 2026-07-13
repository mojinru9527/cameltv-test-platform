"""lanhu_evidence_pack — 蓝湖证据包 OCR 四张表

创建 4 张表:
- lanhu_evidence_job: 一次证据包采集任务
- lanhu_evidence_page: 页面树中的一个蓝湖页面
- lanhu_evidence_asset: 截图 / Word / JSON / 文件资产
- lanhu_ocr_block: 单张截图的 OCR 输出块

Revision ID: 20260713_lanhu_evidence_pack
Revises: 20260713_merge_dual_heads
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_lanhu_evidence_pack"
down_revision: Union[str, None] = "20260713_merge_dual_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard: tables may already exist from SQLAlchemy auto-create on startup
    from sqlalchemy import inspect as sa_inspect
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing = set(inspector.get_table_names())

    if "lanhu_evidence_job" not in existing:
        op.create_table(
            "lanhu_evidence_job",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("source_url", sa.Text(), nullable=False, server_default=""),
            sa.Column("doc_id", sa.String(200), nullable=False, server_default="", index=True),
            sa.Column("version_id", sa.String(200), nullable=False, server_default="", index=True),
            sa.Column("root_page_id", sa.String(200), nullable=False, server_default="", index=True),
            sa.Column("document_name", sa.String(500), nullable=False, server_default=""),
            sa.Column("status", sa.String(50), nullable=False, server_default="pending", index=True),
            sa.Column("stage", sa.String(50), nullable=False, server_default="queued"),
            sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("captured_pages", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ocr_pages", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_pages", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("word_path", sa.String(1000), nullable=False, server_default=""),
            sa.Column("json_path", sa.String(1000), nullable=False, server_default=""),
            sa.Column("storage_dir", sa.String(1000), nullable=False, server_default=""),
            sa.Column("quality_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("creator_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lanhu_evidence_job_project_status", "lanhu_evidence_job", ["project_id", "status"])
        op.create_index("ix_lanhu_evidence_job_project_doc_ver", "lanhu_evidence_job", ["project_id", "doc_id", "version_id"])

    if "lanhu_evidence_page" not in existing:
        op.create_table(
            "lanhu_evidence_page",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False, index=True),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("page_id", sa.String(200), nullable=False, server_default="", index=True),
            sa.Column("page_name", sa.String(500), nullable=False, server_default=""),
            sa.Column("page_path", sa.String(1000), nullable=False, server_default=""),
            sa.Column("folder", sa.String(1000), nullable=False, server_default=""),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("page_url", sa.Text(), nullable=False, server_default=""),
            sa.Column("local_url", sa.Text(), nullable=False, server_default=""),
            sa.Column("capture_status", sa.String(50), nullable=False, server_default="pending", index=True),
            sa.Column("ocr_status", sa.String(50), nullable=False, server_default="pending", index=True),
            sa.Column("dom_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("ocr_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("merged_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("segment_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("quality_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lanhu_evidence_page_job_order", "lanhu_evidence_page", ["job_id", "order_index"])
        op.create_index("ix_lanhu_evidence_page_project_page", "lanhu_evidence_page", ["project_id", "page_id"])

    if "lanhu_evidence_asset" not in existing:
        op.create_table(
            "lanhu_evidence_asset",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False, index=True),
            sa.Column("page_id", sa.Integer(), nullable=True, index=True),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("asset_type", sa.String(50), nullable=False, server_default="", index=True),
            sa.Column("file_path", sa.Text(), nullable=False, server_default=""),
            sa.Column("relative_path", sa.Text(), nullable=False, server_default=""),
            sa.Column("mime_type", sa.String(100), nullable=False, server_default=""),
            sa.Column("width", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("height", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("scroll_top", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("viewport_height", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sha256", sa.String(64), nullable=False, server_default="", index=True),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lanhu_evidence_asset_job_page_type", "lanhu_evidence_asset", ["job_id", "page_id", "asset_type"])

    if "lanhu_ocr_block" not in existing:
        op.create_table(
            "lanhu_ocr_block",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False, index=True),
            sa.Column("page_id", sa.Integer(), nullable=False, index=True),
            sa.Column("asset_id", sa.Integer(), nullable=False, index=True),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("text", sa.Text(), nullable=False, server_default=""),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("bbox_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_lanhu_ocr_block_job_page_asset", "lanhu_ocr_block", ["job_id", "page_id", "asset_id"])


def downgrade() -> None:
    op.drop_table("lanhu_ocr_block")
    op.drop_table("lanhu_evidence_asset")
    op.drop_table("lanhu_evidence_page")
    op.drop_table("lanhu_evidence_job")
