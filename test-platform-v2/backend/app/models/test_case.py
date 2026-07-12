"""测试用例模型。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.test_case_review import TestCaseReviewTransition


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_case"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)

    # 用例标识
    case_id: Mapped[str] = mapped_column(default="")       # TC-ADMIN-NEWS-001
    title: Mapped[str] = mapped_column(default="")

    # 新分类体系
    domain: Mapped[str] = mapped_column(default="", index=True)   # 用户端 / 运营后台 / 接口测试
    module: Mapped[str] = mapped_column(default="", index=True)   # 首页推荐 / 资讯文章 / ...

    # 用例属性
    case_type: Mapped[str] = mapped_column(default="manual")      # api / manual / ui
    priority: Mapped[str] = mapped_column(default="P2")           # P0 / P1 / P2 / P3
    status: Mapped[str] = mapped_column(default="active")         # draft / active / archived
    tags: Mapped[str] = mapped_column(default="[]")               # JSON 数组

    # 用例内容
    preconditions: Mapped[str] = mapped_column(default="")
    steps: Mapped[str] = mapped_column(default="[]")              # JSON: [{step, desc, expected}]
    expected_result: Mapped[str] = mapped_column(default="")

    # API 关联
    api_method: Mapped[str] = mapped_column(default="")           # GET/POST/PUT/DELETE
    api_endpoint: Mapped[str] = mapped_column(default="")         # /api/v1/xxx
    api_spec_ref: Mapped[str] = mapped_column(default="")         # 旧引用
    api_headers: Mapped[str] = mapped_column(default="{}")        # JSON: {"Content-Type":"application/json"}
    api_body: Mapped[str] = mapped_column(default="")             # JSON: 请求体
    api_assertions: Mapped[str] = mapped_column(default="[]")     # JSON: 断言规则数组

    # 来源追溯
    source: Mapped[str] = mapped_column(default="migration")      # manual / swagger_import / migration / ai_generated
    source_doc_id: Mapped[int | None] = mapped_column(default=None, index=True)  # 来源需求文档 ID
    old_id: Mapped[int | None] = mapped_column(default=None)      # 旧库原始 ID

    # 评审
    review_status: Mapped[str] = mapped_column(default="draft")   # draft / submitted / approved / rejected
    review_comment: Mapped[str] = mapped_column(default="")       # 评审意见
    reviewer_id: Mapped[int] = mapped_column(default=0)           # 评审人 ID

    # 关系
    review_transitions: Mapped[list["TestCaseReviewTransition"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="TestCaseReviewTransition.created_at"
    )
