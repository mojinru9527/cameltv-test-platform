"""Project-scoped domain and module categories for test cases."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class TestCaseDomain(Base, TimestampMixin):
    __tablename__ = "test_case_domain"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_test_case_domain_project_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(100))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    modules: Mapped[list["TestCaseModule"]] = relationship(
        back_populates="domain", order_by="TestCaseModule.id"
    )


class TestCaseModule(Base, TimestampMixin):
    __tablename__ = "test_case_module"
    __table_args__ = (
        UniqueConstraint("domain_id", "name", name="uq_test_case_module_domain_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    domain_id: Mapped[int] = mapped_column(
        ForeignKey("test_case_domain.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    domain: Mapped[TestCaseDomain] = relationship(back_populates="modules")
