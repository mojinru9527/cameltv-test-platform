"""Batch 103 — 用例质量与接口可视字段。

Revision ID: 20260806_batch103_case_quality
Revises: 20260728_merge_batch37_main
Create Date: 2026-08-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_batch103_case_quality"
down_revision: str = "20260728_merge_batch37_main"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 初始迁移会按当前模型 Base.metadata.create_all 建表（含后续模型字段），
    # 因此本迁移必须幂等：列已存在（模型建表）时跳过（仓库既有模式，见 20260626_0003）。
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("test_case")}
    new_columns = [
        ("case_design_method", sa.String(length=64)),
        ("positive_negative", sa.String(length=16)),
        ("test_data_note", sa.Text()),
        ("last_response_json", sa.Text()),
        ("last_run_status", sa.String(length=16)),
    ]
    for name, col_type in new_columns:
        if name not in columns:
            op.add_column("test_case", sa.Column(name, col_type, nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("test_case", "last_run_status")
    op.drop_column("test_case", "last_response_json")
    op.drop_column("test_case", "test_data_note")
    op.drop_column("test_case", "positive_negative")
    op.drop_column("test_case", "case_design_method")
