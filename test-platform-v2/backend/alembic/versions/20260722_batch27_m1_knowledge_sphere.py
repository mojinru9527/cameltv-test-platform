"""Batch 27 M1 — knowledge sphere data models.

Create tables:
  - release_bundle          (release package: client + admin versions + global nav)
  - requirement_module      (hierarchical module→page→function-point tree)
  - module_admin_link       (cross-system linkage: client↔admin module)

Extend tables:
  - requirement_document    (+platform, +doc_type)
  - knowledge_source        (+module_id)

Revision ID: 20260722_batch27_m1_knowledge_sphere
Revises: 20260719_perf_tables, 20260721_knowledge_module_name (merge)
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_batch27_m1_knowledge_sphere"
down_revision: Union[str, tuple[str, ...], None] = ("20260719_perf_tables", "20260721_knowledge_module_name")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    # ── release_bundle ──
    if "release_bundle" not in insp.get_table_names():
        op.create_table(
            "release_bundle",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("name", sa.String(500), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("client_version", sa.String(100), nullable=False, server_default="", index=True),
            sa.Column("admin_version", sa.String(100), nullable=False, server_default="", index=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft", index=True),
            sa.Column("release_date", sa.Date(), nullable=True),
            sa.Column("parent_bundle_id", sa.Integer(),
                      sa.ForeignKey("release_bundle.id", ondelete="SET NULL"),
                      nullable=True, index=True),
            sa.Column("diff_summary", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("global_navigation", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # ── requirement_module ──
    if "requirement_module" not in insp.get_table_names():
        op.create_table(
            "requirement_module",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("release_bundle_id", sa.Integer(),
                      sa.ForeignKey("release_bundle.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("name", sa.String(500), nullable=False, server_default=""),
            sa.Column("node_type", sa.String(50), nullable=False, server_default="module", index=True),
            sa.Column("platform", sa.String(20), nullable=False, server_default="", index=True),
            sa.Column("lanhu_page_id", sa.String(500), nullable=False, server_default=""),
            sa.Column("change_type", sa.String(30), nullable=False, server_default="new"),
            sa.Column("parent_module_id", sa.Integer(),
                      sa.ForeignKey("requirement_module.id", ondelete="SET NULL"),
                      nullable=True, index=True),
            sa.Column("source_version", sa.String(50), nullable=False, server_default=""),
            sa.Column("screenshot_urls", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("has_visual_only_content", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("page_interactions", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # ── module_admin_link ──
    if "module_admin_link" not in insp.get_table_names():
        op.create_table(
            "module_admin_link",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("client_module_id", sa.Integer(),
                      sa.ForeignKey("requirement_module.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("admin_module_id", sa.Integer(),
                      sa.ForeignKey("requirement_module.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("relation_type", sa.String(50), nullable=False, server_default="links_to_admin", index=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # ── requirement_document: +platform +doc_type ──
    rd_cols = {c["name"] for c in insp.get_columns("requirement_document")}
    if "platform" not in rd_cols:
        op.add_column("requirement_document",
                       sa.Column("platform", sa.String(20), nullable=False, server_default=""))
        op.create_index(op.f("ix_requirement_document_platform"),
                        "requirement_document", ["platform"])
    if "doc_type" not in rd_cols:
        op.add_column("requirement_document",
                       sa.Column("doc_type", sa.String(20), nullable=False, server_default="lanhu"))

    # ── knowledge_source: +module_id ──
    ks_cols = {c["name"] for c in insp.get_columns("knowledge_source")}
    if "module_id" not in ks_cols:
        op.add_column("knowledge_source",
                       sa.Column("module_id", sa.Integer(), nullable=True))
        op.create_index(op.f("ix_knowledge_source_module_id"),
                        "knowledge_source", ["module_id"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    # ── knowledge_source: -module_id ──
    ks_cols = {c["name"] for c in insp.get_columns("knowledge_source")}
    if "module_id" in ks_cols:
        op.drop_index(op.f("ix_knowledge_source_module_id"), table_name="knowledge_source")
        op.drop_column("knowledge_source", "module_id")

    # ── requirement_document: -platform -doc_type ──
    rd_cols = {c["name"] for c in insp.get_columns("requirement_document")}
    if "doc_type" in rd_cols:
        op.drop_column("requirement_document", "doc_type")
    if "platform" in rd_cols:
        op.drop_index(op.f("ix_requirement_document_platform"), table_name="requirement_document")
        op.drop_column("requirement_document", "platform")

    # ── module_admin_link ──
    if "module_admin_link" in insp.get_table_names():
        op.drop_table("module_admin_link")

    # ── requirement_module ──
    if "requirement_module" in insp.get_table_names():
        op.drop_table("requirement_module")

    # ── release_bundle ──
    if "release_bundle" in insp.get_table_names():
        op.drop_table("release_bundle")
