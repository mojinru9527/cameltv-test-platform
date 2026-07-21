"""Requirement document model — stores uploaded PRD / xlsx / lanhu links."""
from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class RequirementDocument(Base, TimestampMixin):
    __tablename__ = "requirement_document"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    creator_id: Mapped[int] = mapped_column(default=0)        # user who uploaded the requirement
    title: Mapped[str] = mapped_column(default="")
    file_type: Mapped[str] = mapped_column(default="")       # md / docx / xlsx / lanhu
    source_ref: Mapped[str] = mapped_column(default="")       # original filename or URL
    content: Mapped[str] = mapped_column(default="")          # parsed plain text
    ai_raw: Mapped[str] = mapped_column(default="")           # raw AI JSON response
    status: Mapped[str] = mapped_column(default="uploaded")   # uploaded / parsed / generated / imported
    imported_count: Mapped[int] = mapped_column(default=0)
    imported_func_count: Mapped[int] = mapped_column(default=0)
    imported_api_count: Mapped[int] = mapped_column(default=0)
    imported_func_indices: Mapped[str] = mapped_column(default="[]")   # JSON array of imported func case indices
    imported_api_indices: Mapped[str] = mapped_column(default="[]")    # JSON array of imported api case indices
    extraction_raw: Mapped[str] = mapped_column(default="")            # Stage 1 AI extraction JSON (modules + function_points)
    extraction_status: Mapped[str] = mapped_column(default="not_started")  # not_started|pending_review|confirmed
    # ── Platform & doc type (batch-27 M1) ──
    platform: Mapped[str] = mapped_column(
        default="", index=True
    )  # APP | PC | WEB | ADMIN — which platform the doc belongs to
    doc_type: Mapped[str] = mapped_column(
        default="lanhu"
    )  # lanhu | prd | attachment | manual — document origin type

    # ── Version diff fields (batch-26) ──
    doc_id: Mapped[str] = mapped_column(default="", index=True)          # stable lanhu document id across versions
    version: Mapped[str] = mapped_column(default="")                     # parsed version string (e.g. "14.2.0")
    parent_id: Mapped[int | None] = mapped_column(default=None, index=True)  # previous version's requirement_document.id
    diff_json: Mapped[str] = mapped_column(default="")                   # structured page-level diff JSON
    diff_status: Mapped[str] = mapped_column(default="initial")          # "initial" | "update"
