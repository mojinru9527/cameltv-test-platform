"""Dataset model — parameterized test data for API test execution."""
from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class Dataset(Base, TimestampMixin):
    __tablename__ = "dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(10), default="csv")  # csv | json | sql
    raw_content: Mapped[str] = mapped_column(Text, default="")  # CSV/JSON text content
    sql_query: Mapped[str] = mapped_column(Text, default="")    # SQL query (for sql type)
    connection_string: Mapped[str] = mapped_column(String(500), default="")  # encrypted for sql type
    row_count: Mapped[int] = mapped_column(default=0)
    columns_meta: Mapped[str] = mapped_column(Text, default="[]")  # JSON: ["col1", "col2", ...]
