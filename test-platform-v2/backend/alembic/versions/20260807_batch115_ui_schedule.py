"""batch115_ui_job_schedule

Revision ID: 20260807_batch115_ui_schedule
Revises: 20260806_batch106_project_invite
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260807_batch115_ui_schedule"
down_revision: Union[str, None] = "20260806_batch106_project_invite"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    import sqlalchemy as _sa
    insp = _sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_table(bind, table: str) -> bool:
    import sqlalchemy as _sa
    return table in _sa.inspect(bind).get_table_names()


def upgrade() -> None:
    # test_schedule / ui_test_job 由 AUTO_CREATE_TABLES（模型元数据）建表，无 create 迁移；
    # 裸库迁移测试（stamp 旧 rev 后 upgrade）中两表不存在 → 直接跳过，避免 NoSuchTableError。
    bind = op.get_bind()
    if not _has_table(bind, "test_schedule") or not _has_table(bind, "ui_test_job"):
        return
    # B112-3：UI job 定时 —— schedule 支持 job_type=ui（plan_id 允许为空）
    # 幂等：CI 干净检出会先用模型建表（AUTO_CREATE_TABLES），列已存在时跳过，避免 duplicate column。
    if not _has_column(bind, "test_schedule", "job_type"):
        op.add_column("test_schedule", sa.Column("job_type", sa.String(length=10), nullable=False, server_default="plan"))
    if not _has_column(bind, "test_schedule", "job_id"):
        op.add_column("test_schedule", sa.Column("job_id", sa.Integer(), nullable=True))
    # SQLite does not implement ALTER COLUMN. Alembic's batch operation recreates
    # the table there while still emitting a regular ALTER on PostgreSQL.
    with op.batch_alter_table("test_schedule") as batch_op:
        batch_op.alter_column("plan_id", existing_type=sa.Integer(), nullable=True)
    indexes = {i["name"] for i in sa.inspect(bind).get_indexes("test_schedule")}
    if "ix_test_schedule_job_id" not in indexes:
        op.create_index("ix_test_schedule_job_id", "test_schedule", ["job_id"])
    # UiTestJob 定时字段
    if not _has_column(bind, "ui_test_job", "cron_expression"):
        op.add_column("ui_test_job", sa.Column("cron_expression", sa.String(length=100), nullable=False, server_default=""))
    if not _has_column(bind, "ui_test_job", "schedule_enabled"):
        op.add_column("ui_test_job", sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("ui_test_job", "schedule_enabled")
    op.drop_column("ui_test_job", "cron_expression")
    op.drop_index("ix_test_schedule_job_id", table_name="test_schedule")
    op.drop_column("test_schedule", "job_id")
    op.drop_column("test_schedule", "job_type")
    with op.batch_alter_table("test_schedule") as batch_op:
        batch_op.alter_column("plan_id", existing_type=sa.Integer(), nullable=False)
