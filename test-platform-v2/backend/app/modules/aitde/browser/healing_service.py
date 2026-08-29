"""AITDE V3.3 ActionHealingService (V33-011).

Persistence layer for Action Healing Proposals. The pure diff/guard logic lives in
:mod:`app.modules.aitde.browser.healing` (``HealingGuard``); this service runs the
guard over a before/after IR pair, records the resulting proposal (OPEN for
action-only diffs, REJECTED + audited for an oracle/contract mutation), and lets a
reviewer list, approve or reject proposals. Healing can never mutate the frozen
oracle/contract: an oracle-touching proposal is rejected wholesale and persisted
for audit, and only an OPEN action-only proposal may be approved.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.browser.healing import HealingGuard
from app.modules.aitde.browser.models import HealingProposal
from app.modules.aitde.common.enums import HealingProposalStatus

_REVIEWABLE = {HealingProposalStatus.OPEN.value}


def _serialize(node: Any) -> str:
    return json.dumps(node, ensure_ascii=False)


def create_proposal(
    db: Session,
    scenario_adapter_id: int,
    command_plan_version_id: int,
    before_ir: dict[str, Any],
    after_ir: dict[str, Any],
    reason: str,
    created_by_type: str = "AI",
    evidence_refs: list[int] | None = None,
) -> HealingProposal:
    """Build + persist an Action Healing Proposal from a before/after IR diff.

    The ``HealingGuard`` decides whether the change is an allowed action-only diff
    (-> OPEN) or an oracle/contract mutation (-> REJECTED, audit). An OPEN
    proposal may later be approved; a REJECTED proposal is immutable at OPEN.
    """
    guard = HealingGuard()
    result = guard.create_proposal(before_ir, after_ir, reason)
    proposal = HealingProposal(
        scenario_adapter_id=scenario_adapter_id,
        command_plan_version_id=command_plan_version_id,
        proposal_type=result["proposal_type"],
        before_json=_serialize(result.get("before_json", before_ir)),
        after_json=_serialize(result.get("after_json", after_ir)),
        reason=result["reason"],
        evidence_refs_json=_serialize(evidence_refs or []),
        status=result["status"],
        created_by_type=created_by_type,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def get_proposal(db: Session, proposal_id: int) -> HealingProposal:
    p = db.get(HealingProposal, proposal_id)
    if not p:
        raise APIException(code=404, msg="愈合提案不存在", http_status=404)
    return p


def list_proposals(
    db: Session,
    scenario_adapter_id: int | None = None,
    status: str | None = None,
) -> list[HealingProposal]:
    stmt = select(HealingProposal)
    if scenario_adapter_id is not None:
        stmt = stmt.where(HealingProposal.scenario_adapter_id == scenario_adapter_id)
    if status is not None:
        stmt = stmt.where(HealingProposal.status == status)
    stmt = stmt.order_by(HealingProposal.created_at.desc())
    return list(db.scalars(stmt).all())


def approve_proposal(
    db: Session, proposal_id: int, reviewed_by: int
) -> HealingProposal:
    """Approve an OPEN Action-only Healing Proposal.

    Only an action-only (non-oracle) proposal may be approved; an oracle/contract
    mutation is immutable REJECTED and can never be flipped to APPROVED.
    """
    p = get_proposal(db, proposal_id)
    if p.status != HealingProposalStatus.OPEN.value:
        raise APIException(
            code=409,
            msg=f"提案状态不是 OPEN，无法批准：{p.status}",
            http_status=409,
        )
    p.status = HealingProposalStatus.APPROVED.value
    p.reviewed_by = reviewed_by
    p.reviewed_at = datetime.now()
    db.commit()
    db.refresh(p)
    return p


def reject_proposal(db: Session, proposal_id: int, reviewed_by: int) -> HealingProposal:
    """Reject an OPEN Action-only Healing Proposal."""
    p = get_proposal(db, proposal_id)
    if p.status != HealingProposalStatus.OPEN.value:
        raise APIException(
            code=409,
            msg=f"提案状态不是 OPEN，无法拒绝：{p.status}",
            http_status=409,
        )
    p.status = HealingProposalStatus.REJECTED.value
    p.reviewed_by = reviewed_by
    p.reviewed_at = datetime.now()
    db.commit()
    db.refresh(p)
    return p


def to_dict(p: HealingProposal) -> dict[str, Any]:
    """Compact, JSON-safe representation for API responses.

    Parses the stored JSON-string columns back to objects so the frontend can
    render the before/after diff without doing its own deserialization.
    """
    return {
        "id": p.id,
        "scenario_adapter_id": p.scenario_adapter_id,
        "command_plan_version_id": p.command_plan_version_id,
        "proposal_type": p.proposal_type,
        "before_json": json.loads(p.before_json or "{}"),
        "after_json": json.loads(p.after_json or "{}"),
        "reason": p.reason,
        "evidence_refs_json": json.loads(p.evidence_refs_json or "[]"),
        "status": p.status,
        "created_by_type": p.created_by_type,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "reviewed_by": p.reviewed_by,
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
    }
