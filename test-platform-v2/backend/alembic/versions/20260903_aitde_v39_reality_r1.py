"""aitde v3.9-R1 reality gate: oracle binding + assertion trust + evidence integrity

Revision ID: 20260903_aitde_v39_reality_r1
Revises: 20260902_aitde_v38_aiclosed
Create Date: 2026-09-03 00:30:00

V3.9 Reality Gate (R1 Trust Chain) migration:
- ``scenario_oracle_bindings``: binds a real TestOracle to an observation selector
  on an adapter; Expected stays only on TestOracle.
- ``assertion_results``: adds ``test_oracle_id`` / ``oracle_source_type`` /
  ``trust_status`` / ``binding_id`` so a PASS can be traced to a trusted Oracle.
- ``evidence_artifacts``: adds physical-integrity columns so a 0-byte / empty-hash
  / missing-object artifact can never satisfy a Required Evidence.
- ``execution_steps``: adds ``evidence_refs_json`` so each step references its
  real EvidenceArtifact ids.

Idempotent guards follow the b191 convention (stamp-replay self-heals).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_aitde_v39_reality_r1"
down_revision: Union[str, None] = "20260902_aitde_v38_aiclosed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "scenario_oracle_bindings" not in inspector.get_table_names():
        op.create_table(
            "scenario_oracle_bindings",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_adapter_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("scenario_version_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("oracle_id", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
            sa.Column("binding_type", sa.String(16), nullable=False, server_default=sa.text("'API_JSONPATH'"), index=True),
            sa.Column("source_step_key", sa.String(128), nullable=False, server_default=sa.text("''")),
            sa.Column("observation_selector_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
            sa.Column("binding_version", sa.String(16), nullable=False, server_default=sa.text("'1.0'")),
            sa.Column("created_at", sa.DateTime, nullable=True),
            sa.Column("validated_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint(
                "scenario_version_id", "oracle_id", "binding_type",
                name="uq_scenario_oracle_binding",
            ),
        )

    # assertion_results trust columns.
    if _has_column(inspector, "assertion_results", "test_oracle_id") is False:
        op.add_column(
            "assertion_results",
            sa.Column("test_oracle_id", sa.Integer, nullable=True, index=True),
        )
    if _has_column(inspector, "assertion_results", "oracle_source_type") is False:
        op.add_column(
            "assertion_results",
            sa.Column("oracle_source_type", sa.String(32), nullable=True, server_default=sa.text("'LEGACY_EXECUTION'"), index=True),
        )
    if _has_column(inspector, "assertion_results", "trust_status") is False:
        op.add_column(
            "assertion_results",
            sa.Column("trust_status", sa.String(32), nullable=True, server_default=sa.text("'LEGACY_UNVERIFIED'"), index=True),
        )
    if _has_column(inspector, "assertion_results", "binding_id") is False:
        op.add_column(
            "assertion_results",
            sa.Column("binding_id", sa.Integer, nullable=True),
        )

    # evidence_artifacts physical-integrity columns.
    if _has_column(inspector, "evidence_artifacts", "integrity_status") is False:
        op.add_column(
            "evidence_artifacts",
            sa.Column("integrity_status", sa.String(16), nullable=True, server_default=sa.text("'PENDING'"), index=True),
        )
    if _has_column(inspector, "evidence_artifacts", "storage_verified_at") is False:
        op.add_column(
            "evidence_artifacts",
            sa.Column("storage_verified_at", sa.DateTime, nullable=True),
        )
    if _has_column(inspector, "evidence_artifacts", "sanitizer_version") is False:
        op.add_column(
            "evidence_artifacts",
            sa.Column("sanitizer_version", sa.String(32), nullable=True),
        )
    if _has_column(inspector, "evidence_artifacts", "storage_etag") is False:
        op.add_column(
            "evidence_artifacts",
            sa.Column("storage_etag", sa.String(128), nullable=True),
        )

    # execution_steps evidence refs.
    if _has_column(inspector, "execution_steps", "evidence_refs_json") is False:
        op.add_column(
            "execution_steps",
            sa.Column("evidence_refs_json", sa.Text, nullable=True, server_default=sa.text("'[]'")),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for col, table in (
        ("evidence_refs_json", "execution_steps"),
        ("storage_etag", "evidence_artifacts"),
        ("sanitizer_version", "evidence_artifacts"),
        ("storage_verified_at", "evidence_artifacts"),
        ("integrity_status", "evidence_artifacts"),
        ("binding_id", "assertion_results"),
        ("trust_status", "assertion_results"),
        ("oracle_source_type", "assertion_results"),
        ("test_oracle_id", "assertion_results"),
    ):
        if _has_column(inspector, table, col):
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_column(col)

    if "scenario_oracle_bindings" in inspector.get_table_names():
        op.drop_table("scenario_oracle_bindings")
