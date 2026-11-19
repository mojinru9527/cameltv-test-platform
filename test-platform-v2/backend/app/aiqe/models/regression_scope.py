"""V16-008：Regression Scope Snapshot（服务端计算、不可由 AI 缩小）。

- 记录 scope/规则版本/输入证据 refs/必测集合/related/smoke/原因/审批人/checksum；
- checksum 为 canonical JSON 的 sha256，重复相同输入复用同一条（幂等）；
- Launch 与服务端 gate 只读取该快照，不接受调用方自报 scope。
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

RULE_VERSION = "V16-008.1"


class RegressionScopeSnapshot(Base):
    __tablename__ = "aiqe_regression_scopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    defect_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(48), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False, default=RULE_VERSION)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mandatory_refs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mandatory_node_keys_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    related_node_keys_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    smoke_node_keys_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    excluded_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    reasons_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index(
            "uq_aiqe_regression_scopes_checksum",
            "project_id",
            "defect_id",
            "checksum_sha256",
            unique=True,
        ),
    )


def scope_checksum(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def scope_payload(
    *,
    scope: str,
    rule_version: str,
    mandatory_refs: list[str],
    mandatory_node_keys: list[str],
    related_node_keys: list[str],
    smoke_node_keys: list[str],
    excluded: list[dict[str, Any]],
    reasons: dict[str, str],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scope": scope,
        "rule_version": rule_version,
        "mandatory_refs": sorted(mandatory_refs),
        "mandatory_node_keys": sorted(mandatory_node_keys),
        "related_node_keys": sorted(related_node_keys),
        "smoke_node_keys": sorted(smoke_node_keys),
        "excluded": excluded,
        "reasons": dict(sorted(reasons.items())),
        "inputs": inputs,
    }
