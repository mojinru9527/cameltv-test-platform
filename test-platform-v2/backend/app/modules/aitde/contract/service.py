"""Contract service (V30-052..V30-059)."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    ReviewStatus,
    ScopeDecision,
)
from app.modules.aitde.contract import repository
from app.modules.aitde.contract.models import TestContractVersion
from app.modules.aitde.contract.schemas import (
    ContractDiffRead,
    ContractFreezeRequest,
    ContractGenerateRequest,
    ContractSnapshot,
)
from app.modules.aitde.intelligence.provider import (
    ContractContext,
    IntelligenceProvider,
    LegacyAIServiceProvider,
)
from app.modules.aitde.mission import service as mission_service
from app.modules.aitde.scope import service as scope_svc
from app.modules.aitde.scope import ambiguity_repository


def _freeze_precondition(db: Session, mission_id: int) -> None:
    """Scope complete AND no open P0/P1 ambiguity, else 409."""
    _, scope_summary = scope_svc.list_scope(db, mission_id)
    if scope_summary.total == 0 or scope_summary.review_progress < 1.0:
        raise APIException(
            code=409,
            msg="CONTRACT_PRECONDITION_FAILED: Scope 未完成评审",
            http_status=409,
        )
    if ambiguity_repository.has_open_p0p1(db, mission_id):
        raise APIException(
            code=409,
            msg="CONTRACT_PRECONDITION_FAILED: 存在未解决的 P0/P1 歧义",
            http_status=409,
        )


def _approved_scope_items(db: Session, mission_id: int) -> list[dict]:
    rows, _ = scope_svc.list_scope(db, mission_id)
    return [
        {
            "scope_key": r.scope_key,
            "name": r.name,
            "decision": r.decision,
            "risk_level": r.risk_level,
            "reason": r.reason,
            "review_status": r.review_status,
        }
        for r in rows
        if r.review_status == ReviewStatus.APPROVED.value
        and r.decision == ScopeDecision.INCLUDE.value
    ]


def _approved_intents(db: Session, mission_id: int) -> list[dict]:
    from app.modules.aitde.scope.ambiguity_repository import list_intents as _li

    return [
        {"intent_key": i.intent_key, "title": i.title, "business_goal": i.business_goal}
        for i in _li(db, mission_id)
        if i.review_status == ReviewStatus.APPROVED.value
    ]


def generate(
    db: Session,
    mission_id: int,
    project_id: int,
    user_id: int,
    request: ContractGenerateRequest,
    provider: IntelligenceProvider | None = None,
) -> dict:
    mission_service.get_mission(db, mission_id, project_id)
    _freeze_precondition(db, mission_id)

    contract = repository.get_or_create_identity(db, mission_id, user_id)
    next_no = (contract.current_version_no or 0) + 1

    context = ContractContext(
        mission_id=mission_id,
        scope_items=_approved_scope_items(db, mission_id),
        intents=_approved_intents(db, mission_id),
    )
    prov = provider or LegacyAIServiceProvider()
    snapshot: ContractSnapshot = prov.build_contract(context)

    version = repository.create_version(
        db, contract.id, next_no, snapshot.model_dump(), user_id
    )
    contract.current_version_no = next_no
    db.commit()
    db.refresh(version)
    db.refresh(contract)
    return {"contract_id": contract.id, "version_no": next_no, "version_id": version.id}


def get_current(db: Session, mission_id: int) -> dict:
    contract = repository.get_identity(db, mission_id)
    if not contract:
        raise APIException(code=404, msg="Contract 尚未生成", http_status=404)
    version = repository.latest_version(db, contract.id)
    return {
        "contract_id": contract.id,
        "name": contract.name,
        "version_no": contract.current_version_no,
        "version": _version_to_dict(version) if version else None,
    }


def list_versions(db: Session, contract_id: int) -> list[dict]:
    return [d for d in (_version_to_dict(v) for v in repository.list_versions(db, contract_id)) if d is not None]


def freeze(
    db: Session,
    contract_id: int,
    mission_id: int,
    project_id: int,
    user_id: int,
    request: ContractFreezeRequest,
) -> dict:
    mission = mission_service.get_mission(db, mission_id, project_id)
    if not request.confirm:
        raise APIException(code=400, msg="必须确认冻结", http_status=400)
    _freeze_precondition(db, mission_id)

    version = repository.get_version(db, contract_id, request.expected_version)
    if not version:
        raise APIException(code=404, msg="契约版本不存在", http_status=404)

    version = repository.freeze_version(db, version, user_id)
    mission.current_contract_version_id = version.id
    mission.status = "CONTRACT_FROZEN"
    db.commit()
    db.refresh(mission)
    return {
        "version_no": version.version_no,
        "status": version.status,
        "contract_id": contract_id,
    }


def diff(
    db: Session, contract_id: int, base_no: int, target_no: int
) -> ContractDiffRead:
    base = repository.get_version(db, contract_id, base_no)
    target = repository.get_version(db, contract_id, target_no)
    if not base or not target:
        raise APIException(code=404, msg="契约版本不存在", http_status=404)
    base_rules = {
        r["rule_key"]: r for r in json.loads(base.snapshot_json).get("rules", [])
    }
    target_rules = {
        r["rule_key"]: r for r in json.loads(target.snapshot_json).get("rules", [])
    }

    added, removed, changed = [], [], []
    for key in sorted(target_rules.keys() - base_rules.keys()):
        added.append(
            {
                "rule_key": key,
                "change": "added",
                "title": target_rules[key].get("title"),
            }
        )
    for key in sorted(base_rules.keys() - target_rules.keys()):
        removed.append(
            {
                "rule_key": key,
                "change": "removed",
                "title": base_rules[key].get("title"),
            }
        )
    for key in sorted(base_rules.keys() & target_rules.keys()):
        if base_rules[key] != target_rules[key]:
            changed.append(
                {
                    "rule_key": key,
                    "change": "changed",
                    "title": target_rules[key].get("title"),
                }
            )
    return ContractDiffRead(
        base_version=base_no,
        target_version=target_no,
        added=added,  # type: ignore[arg-type]
        removed=removed,  # type: ignore[arg-type]
        changed=changed,  # type: ignore[arg-type]
    )


def create_change_proposal(
    db: Session, mission_id: int, project_id: int, user_id: int, data: dict
) -> dict:
    mission_service.get_mission(db, mission_id, project_id)
    proposal = repository.create_change_proposal(
        db, mission_id, data, actor="USER", user_id=user_id
    )
    db.commit()
    db.refresh(proposal)
    return {"id": proposal.id, "status": proposal.status}


def _version_to_dict(v: TestContractVersion | None) -> dict | None:
    if v is None:
        return None
    return {
        "id": v.id,
        "contract_id": v.contract_id,
        "version_no": v.version_no,
        "status": v.status,
        "content_hash": v.content_hash,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "approved_at": v.approved_at.isoformat() if v.approved_at else None,
    }
