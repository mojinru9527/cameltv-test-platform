"""AUD-009：部署证明（可信部署记录）。

回归必须证明目标环境**实际运行**的就是 fixed SHA（v1.5 §02 AUD-009 第 2 条）。
Attestation 由 CI/部署流水线写入，回归服务只读，不接受客户端传入的 deployed SHA。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DeploymentAttestation(Base):
    __tablename__ = "aiqe_deployment_attestations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    environment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("environment.id", ondelete="CASCADE"), nullable=True, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    image_digest: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ci")
    evidence_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    attested_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    attested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index(
            "ix_aiqe_deployment_attestations_env_sha",
            "project_id",
            "environment_id",
            "commit_sha",
        ),
    )
