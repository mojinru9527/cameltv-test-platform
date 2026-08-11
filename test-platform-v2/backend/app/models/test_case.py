"""测试用例模型。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.test_case_review import TestCaseReviewTransition


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_case"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "source_doc_id",
            "source_case_index",
            name="uq_test_case_ai_source_index",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)

    # 用例标识
    case_id: Mapped[str] = mapped_column(default="")       # TC-ADMIN-NEWS-001
    title: Mapped[str] = mapped_column(default="")

    # 新分类体系
    domain: Mapped[str] = mapped_column(default="", index=True)   # 用户端 / 运营后台 / 接口测试
    module: Mapped[str] = mapped_column(default="", index=True)   # 首页推荐 / 资讯文章 / ...

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)

    # 用例属性
    case_type: Mapped[str] = mapped_column(default="manual")      # api / manual / ui
    priority: Mapped[str] = mapped_column(default="P2")           # P0 / P1 / P2 / P3
    status: Mapped[str] = mapped_column(default="active")         # draft / active / archived
    tags: Mapped[str] = mapped_column(default="[]")               # JSON 数组
    # 用例设计追溯（batch-103：规范对齐）
    case_design_method: Mapped[str] = mapped_column(default="")    # 等价类划分/边界值分析/场景法/错误推测/组合覆盖
    positive_negative: Mapped[str] = mapped_column(default="")     # positive/negative/boundary
    test_data_note: Mapped[str] = mapped_column(Text, default="")  # 输入数据业务含义与来源

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
    api_assertions: Mapped[str] = mapped_column(default="[]")
    depends_on_ids: Mapped[str] = mapped_column(Text, default="[]")  # C107-2 前置接口用例 id 数组     # JSON: 断言规则数组
    last_response_json: Mapped[str] = mapped_column(Text, default="")  # JSON: 最近执行实际响应
    last_run_status: Mapped[str] = mapped_column(default="")       # success/fail/skipped/error
    dataset_id: Mapped[int | None] = mapped_column(default=None)  # C147-8 默认数据集

    # API 追溯 (batch-34: FK 链路补齐)
    api_endpoint_id: Mapped[int | None] = mapped_column(default=None, index=True)  # FK → ApiEndpoint
    requirement_module_id: Mapped[int | None] = mapped_column(default=None, index=True)  # FK → RequirementModule

    # 来源追溯
    source: Mapped[str] = mapped_column(default="migration")      # manual / swagger_import / migration / ai_generated
    source_req_id: Mapped[str] = mapped_column(default="", index=True)  # 外部需求标识
    source_doc_id: Mapped[int | None] = mapped_column(default=None, index=True)  # 来源需求文档 ID
    source_case_index: Mapped[int | None] = mapped_column(default=None, index=True)  # AI 结果中的稳定全局索引
    old_id: Mapped[int | None] = mapped_column(default=None)      # 旧库原始 ID

    # 评审
    review_status: Mapped[str] = mapped_column(default="draft")   # draft / submitted / approved / rejected
    review_comment: Mapped[str] = mapped_column(default="")       # 评审意见
    reviewer_id: Mapped[int] = mapped_column(default=0)           # 评审人 ID

    # 关系
    review_transitions: Mapped[list["TestCaseReviewTransition"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="TestCaseReviewTransition.created_at"
    )
