"""Repair scenario review states and contract-version lineage labels.

Revision ID: 20260913_b231_traceability_truth
Revises: 20260912_b231_execution_truth
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260913_b231_traceability_truth"
down_revision: Union[str, None] = "20260912_b231_execution_truth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "test_scenario_versions" in tables:
        bind.execute(
            sa.text(
                """
                UPDATE test_scenario_versions
                   SET review_status = CASE LOWER(review_status)
                       WHEN 'approve' THEN 'APPROVED'
                       WHEN 'approved' THEN 'APPROVED'
                       WHEN 'reject' THEN 'REJECTED'
                       WHEN 'rejected' THEN 'REJECTED'
                       WHEN 'request_change' THEN 'REQUEST_CHANGE'
                       WHEN 'proposed' THEN 'PROPOSED'
                       ELSE review_status
                   END
                """
            )
        )
    if "lineage_edges" in tables:
        bind.execute(
            sa.text(
                """
                DELETE FROM lineage_edges AS bad
                 WHERE bad.from_type = 'CONTRACT_RULE'
                   AND bad.edge_type = 'CONTRACTED_FOR'
                   AND EXISTS (
                       SELECT 1 FROM lineage_edges AS good
                        WHERE good.project_id = bad.project_id
                          AND good.from_type = 'CONTRACT_VERSION'
                          AND good.from_id = bad.from_id
                          AND good.to_type = bad.to_type
                          AND good.to_id = bad.to_id
                          AND good.edge_type = bad.edge_type
                   )
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE lineage_edges
                   SET from_type = 'CONTRACT_VERSION'
                 WHERE from_type = 'CONTRACT_RULE'
                   AND edge_type = 'CONTRACTED_FOR'
                """
            )
        )


def downgrade() -> None:
    # Truth repair is intentionally irreversible.
    pass
