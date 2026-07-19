"""Reconcile cases hidden by deleted categories and retire legacy API cases.

Revision ID: 20260716_case_cleanup
Revises: 20260715_test_case_categories
Create Date: 2026-07-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260716_case_cleanup"
down_revision: Union[str, None] = "20260715_test_case_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if not {"test_case", "test_case_domain", "test_case_module"}.issubset(tables):
        return

    # This is intentionally idempotent. It reconciles data created before
    # category deletion cascaded to test_case.is_deleted and retires the old
    # API cases that are now managed by the dedicated API testing module.
    op.execute(
        sa.text(
            """
            UPDATE test_case AS tc
            SET is_deleted = true
            WHERE tc.is_deleted = false
              AND (
                tc.case_type = 'api'
                OR tc.domain = '接口测试'
                OR EXISTS (
                    SELECT 1
                    FROM test_case_domain AS d
                    WHERE d.project_id = tc.project_id
                      AND d.name = tc.domain
                      AND d.is_deleted = true
                )
                OR EXISTS (
                    SELECT 1
                    FROM test_case_module AS m
                    JOIN test_case_domain AS d ON d.id = m.domain_id
                    WHERE m.project_id = tc.project_id
                      AND d.project_id = tc.project_id
                      AND d.name = tc.domain
                      AND m.name = tc.module
                      AND m.is_deleted = true
                )
              )
            """
        )
    )


def downgrade() -> None:
    # Logical deletion cannot be safely reversed because user-initiated and
    # migration-initiated deletions share the same marker.
    pass
