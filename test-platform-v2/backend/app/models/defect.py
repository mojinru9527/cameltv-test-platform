"""Defect ORM model + transition history."""
from __future__ import annotations

from datetime import UTC, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Defect(Base):
    __tablename__ = "defect"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    defect_id: Mapped[str] = mapped_column(String(50), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="P2")       # P0/P1/P2/P3
    status: Mapped[str] = mapped_column(String(20), default="open")
    # Statuses: open → confirmed → fixing → pending_review → closed / rejected
    #   rejected / closed → open (reopen)
    case_id: Mapped[Optional[int]] = mapped_column(default=None, index=True)
    execution_id: Mapped[Optional[int]] = mapped_column(default=None)
    aiqe_run_id: Mapped[str | None] = mapped_column(String(36), default=None, index=True)
    aiqe_node_run_id: Mapped[str | None] = mapped_column(String(36), default=None)
    reproduction_steps_json: Mapped[list | None] = mapped_column(JSON, default=None)
    evidence_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    ac_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False)
    aitde_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("execution_runs.id", ondelete="SET NULL"), default=None, index=True
    )
    assignee_id: Mapped[int] = mapped_column(default=0, index=True)
    external_id: Mapped[str] = mapped_column(String(100), default="")     # 禅道/Jira ID
    external_url: Mapped[str] = mapped_column(String(500), default="")    # 外部链接
    creator_id: Mapped[int] = mapped_column(default=0)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    transitions: Mapped[list["DefectTransition"]] = relationship(
        back_populates="defect", order_by="DefectTransition.created_at.asc()",
    )


class DefectTransition(Base):
    """Audit trail for defect status transitions."""
    __tablename__ = "defect_transition"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str] = mapped_column(String(20), default="")
    to_status: Mapped[str] = mapped_column(String(20), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    operator_id: Mapped[int] = mapped_column(default=0)
    operator_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # Relationship back
    defect: Mapped[Defect] = relationship(back_populates="transitions")


class DefectComment(Base):
    """User comments on defects."""
    __tablename__ = "defect_comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    author_id: Mapped[int] = mapped_column(default=0)
    author_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


class DefectAttachment(Base):
    """File attachments on defects — metadata in DB, files on disk."""
    __tablename__ = "defect_attachment"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255), default="")        # original filename
    stored_path: Mapped[str] = mapped_column(String(500), default="")     # relative path on disk
    file_size: Mapped[int] = mapped_column(default=0)                     # bytes
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    uploader_id: Mapped[int] = mapped_column(default=0)
    uploader_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class DefectRegression(Base):
    """缺陷一键回归记录（TA-027 + AUD-009/010）。

    - ``idempotency_fingerprint`` 唯一：同一项目/缺陷/SHA/环境/范围只允许一个回归；
    - ``deployed_sha`` 来自 ``aiqe_deployment_attestations``（不接受客户端自报）；
    - ``scope``/``mandatory_case_ids_json``/``excluded_json`` 冻结执行范围；
    - ``terminal_summary_json``/``comparison_snapshot_id`` 由 Run 终态处理器写入。
    """
    __tablename__ = "defect_regressions"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(
        ForeignKey("defect.id", ondelete="CASCADE"), index=True
    )
    fixed_sha: Mapped[str] = mapped_column(String(40), default="")
    previous_run_id: Mapped[str | None] = mapped_column(String(36), default=None)
    verification_run_id: Mapped[str | None] = mapped_column(String(36), default=None, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    # ── AUD-009 ──
    idempotency_fingerprint: Mapped[str | None] = mapped_column(
        String(64), default=None, unique=True, index=True
    )
    deployed_sha: Mapped[str | None] = mapped_column(String(64), default=None)
    target_environment_id: Mapped[int | None] = mapped_column(default=None)
    source_run_id: Mapped[str | None] = mapped_column(String(36), default=None, index=True)
    workflow_definition_id: Mapped[str | None] = mapped_column(String(36), default=None)
    workflow_checksum: Mapped[str | None] = mapped_column(String(128), default=None)
    profile_checksum: Mapped[str | None] = mapped_column(String(128), default=None)
    scope: Mapped[str] = mapped_column(String(40), default="DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT")
    scope_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    mandatory_case_ids_json: Mapped[list | None] = mapped_column(JSON, default=None)
    selected_case_ids_json: Mapped[list | None] = mapped_column(JSON, default=None)
    excluded_json: Mapped[list | None] = mapped_column(JSON, default=None)
    reason: Mapped[str] = mapped_column(Text, default="")
    request_idempotency_key: Mapped[str | None] = mapped_column(String(128), default=None)
    blockers_json: Mapped[list | None] = mapped_column(JSON, default=None)
    # ── AUD-010 ──
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    terminal_summary_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    failing_case_ids_json: Mapped[list | None] = mapped_column(JSON, default=None)
    assertion_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    evidence_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    comparison_snapshot_id: Mapped[str | None] = mapped_column(String(36), default=None)
    suggestion: Mapped[str | None] = mapped_column(String(32), default=None)
    cancelled_at: Mapped[datetime | None] = mapped_column(default=None)


class RunComparisonSnapshot(Base):
    """AUD-010：不可变 Before/After 对比快照（只追加，不更新）。"""

    __tablename__ = "run_comparison_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    regression_id: Mapped[int | None] = mapped_column(index=True, default=None)
    defect_id: Mapped[int | None] = mapped_column(index=True, default=None)
    source_run_id: Mapped[str | None] = mapped_column(String(36), default=None)
    regression_run_id: Mapped[str | None] = mapped_column(String(36), default=None)
    fixed_sha: Mapped[str] = mapped_column(String(64), default="")
    deployed_sha: Mapped[str] = mapped_column(String(64), default="")
    workflow_checksum: Mapped[str | None] = mapped_column(String(128), default=None)
    outcome: Mapped[str] = mapped_column(String(24), default="")
    assertion_diff_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    node_attempt_diff_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    evidence_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    new_failures_json: Mapped[list | None] = mapped_column(JSON, default=None)
    fixed_failures_json: Mapped[list | None] = mapped_column(JSON, default=None)
    blocked_json: Mapped[list | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
