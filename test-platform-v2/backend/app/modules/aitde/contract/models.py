"""Contract identity + version + change-proposal models (V30-050, M3)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import ContractVersionStatus, ProposalStatus


class TestContract(Base, TimestampMixin):
    __tablename__ = "test_contracts"
    __table_args__ = (UniqueConstraint("mission_id", name="uq_contract_mission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(255), default="Test Contract")
    current_version_no: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(Integer, default=0)


class TestContractVersion(Base, TimestampMixin):
    __tablename__ = "test_contract_versions"
    __table_args__ = (
        UniqueConstraint("contract_id", "version_no", name="uq_contract_version_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(Integer, index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(16), default=ContractVersionStatus.DRAFT.value
    )
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    supersedes_version_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    approved_by: Mapped[int | None] = mapped_column(Integer, default=None)
    approved_at: Mapped[datetime | None] = mapped_column(default=None)


class ChangeProposal(Base, TimestampMixin):
    __tablename__ = "change_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    target_type: Mapped[str] = mapped_column(String(16), default="CONTRACT")
    target_id: Mapped[int] = mapped_column(Integer, default=0)
    target_version: Mapped[int] = mapped_column(Integer, default=0)
    proposal_type: Mapped[str] = mapped_column(String(32), default="modify")
    reason: Mapped[str] = mapped_column(Text, default="")
    diff_json: Mapped[str] = mapped_column(Text, default="{}")
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(16), default=ProposalStatus.OPEN.value, index=True
    )
    reviewed_by: Mapped[int | None] = mapped_column(Integer, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
