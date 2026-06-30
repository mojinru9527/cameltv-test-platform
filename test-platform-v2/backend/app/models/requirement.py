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
