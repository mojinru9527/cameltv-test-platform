"""api_testing_assets — 接口测试资产表

创建 5 张表:
- api_service: 项目下的后端服务分组
- api_import_batch: OpenAPI/Swagger 导入批次
- api_endpoint: 接口资产
- api_execution_task: 批量执行任务
- api_execution_task_item: 任务执行明细

Revision ID: 20260707_0012
Revises: 20260705_0011
Create Date: 2026-07-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260707_0012"
down_revision: Union[str, None] = "20260705_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # api_service
    op.create_table(
        "api_service",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False, index=True),
        sa.Column("display_name", sa.String(), nullable=False, server_default=""),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("default_base_path", sa.String(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_api_service_project_name"),
    )

    # api_import_batch
    op.create_table(
        "api_import_batch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("service_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_type", sa.String(), nullable=False, server_default="openapi"),
        sa.Column("source_ref", sa.String(), nullable=False, server_default=""),
        sa.Column("version", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # api_endpoint
    op.create_table(
        "api_endpoint",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("service_id", sa.Integer(), nullable=False, index=True),
        sa.Column("module", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("method", sa.String(), nullable=False, server_default="GET", index=True),
        sa.Column("path", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("summary", sa.String(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("request_schema", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("response_schema", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("auth_required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deprecated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("source", sa.String(), nullable=False, server_default="manual"),
        sa.Column("import_batch_id", sa.Integer(), nullable=True, index=True),
        sa.Column("version", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "service_id", "method", "path", name="uq_api_endpoint_identity"),
    )

    # api_execution_task
    op.create_table(
        "api_execution_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("task_id", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("environment_id", sa.Integer(), nullable=True, index=True),
        sa.Column("service_id", sa.Integer(), nullable=True, index=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger_type", sa.String(), nullable=False, server_default="manual"),
        sa.Column("creator_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # api_execution_task_item
    op.create_table(
        "api_execution_task_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("case_id", sa.Integer(), nullable=False, index=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("request_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("response_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("assertion_results", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("api_execution_task_item")
    op.drop_table("api_execution_task")
    op.drop_table("api_endpoint")
    op.drop_table("api_import_batch")
    op.drop_table("api_service")
