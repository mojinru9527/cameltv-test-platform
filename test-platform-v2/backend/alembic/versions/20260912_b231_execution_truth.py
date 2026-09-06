"""Repair historical version-task zero-execution results.

Revision ID: 20260912_b231_execution_truth
Revises: 20260911_business_onboarding_context
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_b231_execution_truth"
down_revision: Union[str, None] = "20260911_business_onboarding_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PLAN_FAILURE = (
    '[{"item_id":0,"title":"整体运行","kind":"plan","evidence":"",'
    '"message":"历史运行未执行任何检查；请生成并采纳至少一条可执行方案后重试",'
    '"http_status":null}]'
)
_BLOCKED_COVERAGE = '{"pass":0,"fail":0,"skip":0,"blocked":1}'


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if not {"version_task", "version_task_run"}.issubset(tables):
        return

    bind.execute(
        sa.text(
            """
            UPDATE version_task_run
               SET status = 'blocked',
                   total = 1,
                   blocked = 1,
                   failures = CASE
                       WHEN failures IS NULL OR TRIM(failures) IN ('', '[]')
                       THEN :failure
                       ELSE failures
                   END
             WHERE total = 0
               AND passed = 0
               AND failed = 0
               AND skipped = 0
               AND blocked = 0
               AND status IN ('done', 'blocked')
            """
        ),
        {"failure": _PLAN_FAILURE},
    )
    bind.execute(
        sa.text(
            """
            UPDATE version_task
               SET status = 'blocked', coverage = :coverage
             WHERE status = 'executed'
               AND EXISTS (
                   SELECT 1
                     FROM version_task_run latest
                    WHERE latest.task_id = version_task.id
                      AND latest.id = (
                          SELECT MAX(candidate.id)
                            FROM version_task_run candidate
                           WHERE candidate.task_id = version_task.id
                      )
                      AND latest.status = 'blocked'
                      AND latest.total = 1
                      AND latest.blocked = 1
               )
            """
        ),
        {"coverage": _BLOCKED_COVERAGE},
    )


def downgrade() -> None:
    # Data truth repair is intentionally irreversible.
    pass
