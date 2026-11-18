"""merge v1.5 AUD 链路与 v1.4 PR #595 执行链路

Revision ID: 20261125_merge_aud_v15_pr595
Revises: 20261124_aud020_platform_binding, 20261124_aiqe_pr595_execution

两条链路都从 20261123_ta033_mutation_ledger 分支出来：
- v1.5 AUD-001..020（feature/aiqe-v15-aud-remediation）
- v1.4 PR #595 执行正确性（main）
合并迁移只收敛 head，不新增结构。
"""
from __future__ import annotations

revision = "20261125_merge_aud_v15_pr595"
down_revision = (
    "20261124_aud020_platform_binding",
    "20261124_aiqe_pr595_execution",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """无结构变更：仅合并两个 head。"""


def downgrade() -> None:
    """无结构变更：拆分 head 时无需回滚数据。"""
