"""AUD-014 / AUD-015：Requirement Contract + 结构化 TestCase 模型。

- Contract 冻结后不可原地更新（修改必须新建 revision）；
- AC 必须绑定 Oracle（type/ref/revision 概念），P0 无 Oracle 不得冻结；
- Case 记录 `automation_grade` A–D、`covers_ac_ids`、`platform_targets`、结构化 steps。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RequirementContract(Base):
    __tablename__ = "aiqe_requirement_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    business_goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actors_json: Mapped[list | None] = mapped_column(JSON, default=None)
    business_rules_json: Mapped[list | None] = mapped_column(JSON, default=None)
    ambiguities_json: Mapped[list | None] = mapped_column(JSON, default=None)
    assumptions_json: Mapped[list | None] = mapped_column(JSON, default=None)
    conflicts_json: Mapped[list | None] = mapped_column(JSON, default=None)
    nfr_json: Mapped[list | None] = mapped_column(JSON, default=None)
    source_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    revision_checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT", index=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id", "requirement_id", "revision", name="uq_aiqe_contracts_req_revision"
        ),
        Index("ix_aiqe_contracts_project_status", "project_id", "status"),
    )


class AcceptanceCriterion(Base):
    __tablename__ = "aiqe_acceptance_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("aiqe_requirement_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ac_id: Mapped[str] = mapped_column(String(40), nullable=False)
    given: Mapped[str] = mapped_column(Text, nullable=False, default="")
    when: Mapped[str] = mapped_column(Text, nullable=False, default="")
    then_json: Mapped[list | None] = mapped_column(JSON, default=None)
    priority: Mapped[str] = mapped_column(String(4), nullable=False, default="P2")
    oracle_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    oracle_ref: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    oracle_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    platforms_json: Mapped[list | None] = mapped_column(JSON, default=None)
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("contract_id", "ac_id", name="uq_aiqe_ac_contract_ac"),)


class AiqeTestCase(Base):
    __tablename__ = "aiqe_test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    contract_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("aiqe_requirement_contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    contract_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    covers_ac_ids_json: Mapped[list | None] = mapped_column(JSON, default=None)
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    priority: Mapped[str] = mapped_column(String(4), nullable=False, default="P2")
    preconditions_json: Mapped[list | None] = mapped_column(JSON, default=None)
    fixtures_json: Mapped[list | None] = mapped_column(JSON, default=None)
    platform_targets_json: Mapped[list | None] = mapped_column(JSON, default=None)
    steps_json: Mapped[list | None] = mapped_column(JSON, default=None)
    cleanup_json: Mapped[list | None] = mapped_column(JSON, default=None)
    oracle_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    oracle_ref: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    automation_grade: Mapped[str] = mapped_column(String(1), nullable=False, default="D")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("project_id", "case_id", name="uq_aiqe_cases_project_case"),
        Index("ix_aiqe_cases_contract", "contract_id", "contract_revision"),
    )
