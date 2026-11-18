"""AUD-014：Requirement Contract（来源可追溯 / 版本 / 歧义 / 冻结 / 审批）。

v1.5 §03 AUD-014：

- 每条需求/AC 必须引用真实来源（PRD/Figma/OpenAPI/会议决定/Bug/业务规则），服务端解析；
  不存在的引用标记 ``INVALID_SOURCE_REF`` 并拒绝；
- 状态机 ``DRAFT → REVIEW_REQUIRED → APPROVED → FROZEN → SUPERSEDED``；
- P0 需求必须有批准 Oracle 与验收人；冻结后不可原地更新，只能新建 revision；
- 「立即/实时/尽快/正常/稳定」等模糊词必须询问指标或引用 SLA，不得擅自填数字。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.contract import AcceptanceCriterion, RequirementContract

STATUSES: tuple[str, ...] = (
    "DRAFT",
    "REVIEW_REQUIRED",
    "APPROVED",
    "FROZEN",
    "SUPERSEDED",
)
TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"REVIEW_REQUIRED", "SUPERSEDED"}),
    "REVIEW_REQUIRED": frozenset({"APPROVED", "DRAFT", "SUPERSEDED"}),
    "APPROVED": frozenset({"FROZEN", "SUPERSEDED"}),
    "FROZEN": frozenset({"SUPERSEDED"}),
    "SUPERSEDED": frozenset(),
}
PRIORITIES_REQUIRING_ORACLE: frozenset[str] = frozenset({"P0", "P1"})
VAGUE_TERMS: tuple[str, ...] = ("立即", "实时", "尽快", "正常", "稳定", "及时", "快速")
SOURCE_REF_KINDS: frozenset[str] = frozenset(
    {"prd", "figma", "openapi", "meeting_decision", "bug", "business_rule", "ac", "doc"}
)


class ContractError(ValueError):
    pass


class InvalidSourceRef(ContractError):
    def __init__(self, ref: str, reason: str) -> None:
        super().__init__(f"INVALID_SOURCE_REF: {ref!r} ({reason})")
        self.code = "INVALID_SOURCE_REF"
        self.ref = ref
        self.reason = reason


@dataclass(frozen=True)
class ParsedSourceRef:
    ref: str
    kind: str
    target: str
    detail: dict[str, Any]


def parse_source_ref(ref: str) -> ParsedSourceRef:
    text = str(ref or "").strip()
    if not text or ":" not in text:
        raise InvalidSourceRef(text, "来源引用必须形如 kind:target")
    kind, _, target = text.partition(":")
    kind = kind.strip()
    target = target.strip()
    if kind not in SOURCE_REF_KINDS:
        raise InvalidSourceRef(text, f"未知来源类型: {kind}")
    if not target:
        raise InvalidSourceRef(text, "来源缺少目标")
    detail: dict[str, Any] = {"target": target}
    if kind == "prd":
        # prd:<file>#page/heading/paragraph — 至少要能定位
        if "#" in target:
            file_part, anchor = target.split("#", 1)
            detail.update({"file": file_part, "anchor": anchor})
        else:
            detail.update({"file": target})
        if not detail.get("file"):
            raise InvalidSourceRef(text, "PRD 引用缺少文件")
    elif kind == "openapi":
        parts = target.split(":")
        if len(parts) < 2:
            raise InvalidSourceRef(text, "OpenAPI 引用必须包含 path 与 method")
        detail.update({"path": parts[0], "method": parts[1].upper()})
    elif kind == "figma":
        if not re.match(r"^[0-9a-zA-Z_:-]+$", target):
            raise InvalidSourceRef(text, "Figma 引用必须是 node id 或 URL")
    return ParsedSourceRef(ref=text, kind=kind, target=target, detail=detail)


def resolve_source_ref(db: Session, *, project_id: int, ref: str) -> ParsedSourceRef:
    """服务端解析来源：可校验的类型必须真实存在；其余至少结构合法。"""
    parsed = parse_source_ref(ref)
    if parsed.kind == "bug":
        from app.models.defect import Defect

        defect = db.get(Defect, int(parsed.target)) if parsed.target.isdigit() else None
        if defect is None or int(defect.project_id or 0) != int(project_id):
            raise InvalidSourceRef(ref, "Bug 不存在或不属于当前 Project")
    elif parsed.kind == "ac":
        ac = db.scalar(
            select(AcceptanceCriterion).where(AcceptanceCriterion.ac_id == parsed.target)
        )
        if ac is None:
            raise InvalidSourceRef(ref, "引用的 AC 不存在")
    return parsed


def ambiguity_scan(text: str) -> list[dict[str, str]]:
    """模糊词扫描：命中必须要求指标或 SLA，不能自动填值。"""
    found: list[dict[str, str]] = []
    for term in VAGUE_TERMS:
        if term in str(text or ""):
            found.append({"term": term, "action": "ASK_METRIC_OR_SLA"})
    return found


def compute_checksum(contract: RequirementContract, acs: list[AcceptanceCriterion]) -> str:
    payload = {
        "requirement_id": contract.requirement_id,
        "revision": contract.revision,
        "title": contract.title,
        "business_goal": contract.business_goal,
        "actors": contract.actors_json or [],
        "business_rules": contract.business_rules_json or [],
        "source_refs": contract.source_refs_json or [],
        "acceptance_criteria": sorted(
            (
                {
                    "ac_id": ac.ac_id,
                    "given": ac.given,
                    "when": ac.when,
                    "then": ac.then_json or [],
                    "priority": ac.priority,
                    "oracle_type": ac.oracle_type,
                    "oracle_ref": ac.oracle_ref,
                    "oracle_revision": ac.oracle_revision,
                    "platforms": ac.platforms_json or [],
                }
                for ac in acs
            ),
            key=lambda item: str(item["ac_id"]),
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def get_contract(db: Session, contract_id: str, project_id: int) -> RequirementContract:
    row = db.get(RequirementContract, contract_id)
    if row is None or int(row.project_id or 0) != int(project_id):
        raise ContractError(f"Contract 不存在: {contract_id}")
    return row


def list_acs(db: Session, contract_id: str) -> list[AcceptanceCriterion]:
    return list(
        db.scalars(
            select(AcceptanceCriterion)
            .where(AcceptanceCriterion.contract_id == contract_id)
            .order_by(AcceptanceCriterion.ac_id)
        )
    )


def create_contract_draft(
    db: Session,
    *,
    project_id: int,
    requirement_id: str,
    title: str,
    business_goal: str = "",
    actors: list[str] | None = None,
    business_rules: list[dict[str, Any]] | None = None,
    source_refs: list[str] | None = None,
    acceptance_criteria: list[dict[str, Any]] | None = None,
    created_by: int | None = None,
) -> RequirementContract:
    requirement = str(requirement_id or "").strip()
    if not requirement:
        raise ContractError("requirement_id 不能为空")
    refs = [str(item) for item in (source_refs or []) if str(item).strip()]
    parsed_refs = [
        resolve_source_ref(db, project_id=project_id, ref=ref).ref for ref in refs
    ]
    previous = list(
        db.scalars(
            select(RequirementContract).where(
                RequirementContract.project_id == int(project_id),
                RequirementContract.requirement_id == requirement,
            )
        )
    )
    revision = max((int(row.revision or 0) for row in previous), default=0) + 1
    contract = RequirementContract(
        project_id=int(project_id),
        requirement_id=requirement,
        revision=revision,
        title=str(title or "")[:300],
        business_goal=str(business_goal or ""),
        actors_json=list(actors or []),
        business_rules_json=list(business_rules or []),
        source_refs_json=parsed_refs,
        ambiguities_json=ambiguity_scan(f"{title} {business_goal}"),
        assumptions_json=[],
        conflicts_json=[],
        nfr_json=[],
        status="DRAFT",
        created_by=created_by,
    )
    db.add(contract)
    db.flush()

    acs: list[AcceptanceCriterion] = []
    for index, raw in enumerate(acceptance_criteria or [], start=1):
        if not isinstance(raw, dict):
            raise ContractError("acceptance_criteria 必须是对象数组")
        ac_id = str(raw.get("ac_id") or f"AC-{index:03d}")
        priority = str(raw.get("priority") or "P2").upper()
        oracle_type = str(raw.get("oracle_type") or "")
        oracle_ref = str(raw.get("oracle_ref") or "")
        then = raw.get("then") or raw.get("then_list") or []
        if not isinstance(then, list):
            then = [str(then)]
        ac = AcceptanceCriterion(
            contract_id=contract.id,
            ac_id=ac_id,
            given=str(raw.get("given") or ""),
            when=str(raw.get("when") or ""),
            then_json=[str(item) for item in then],
            priority=priority,
            oracle_type=oracle_type,
            oracle_ref=oracle_ref,
            oracle_revision=raw.get("oracle_revision"),
            platforms_json=list(raw.get("platforms") or []),
            approval_status="PENDING",
        )
        db.add(ac)
        acs.append(ac)
    db.flush()
    contract.revision_checksum = compute_checksum(contract, acs)
    db.flush()
    return contract


def transition_contract(
    db: Session, contract_id: str, target: str, *, project_id: int, actor_id: int | None = None
) -> RequirementContract:
    contract = get_contract(db, contract_id, project_id)
    target = str(target or "").upper()
    if target not in STATUSES:
        raise ContractError(f"未知目标状态: {target}")
    if target not in TRANSITIONS.get(contract.status, frozenset()):
        raise ContractError(f"非法状态迁移: {contract.status} → {target}")
    if target in {"APPROVED", "FROZEN"}:
        _assert_oracle_complete(db, contract)
    contract.status = target
    if target == "APPROVED":
        contract.approved_by = actor_id
        contract.approved_at = datetime.now(UTC)
    if target == "FROZEN":
        contract.frozen_at = datetime.now(UTC)
        contract.revision_checksum = compute_checksum(contract, list_acs(db, contract.id))
    db.flush()
    return contract


def _assert_oracle_complete(db: Session, contract: RequirementContract) -> None:
    acs = list_acs(db, contract.id)
    if not acs:
        raise ContractError("Contract 至少需要 1 条 Acceptance Criteria")
    missing = [
        ac.ac_id
        for ac in acs
        if ac.priority in PRIORITIES_REQUIRING_ORACLE
        and (not ac.oracle_type or not ac.oracle_ref)
    ]
    if missing:
        raise ContractError(f"P0/P1 AC 缺少 Oracle，禁止批准/冻结: {missing}")
    if not contract.source_refs_json:
        raise ContractError("Contract 缺少 source refs，禁止批准/冻结")


def approve_ac(
    db: Session, *, contract_id: str, ac_id: str, project_id: int, approver_id: int
) -> AcceptanceCriterion:
    contract = get_contract(db, contract_id, project_id)
    if contract.status == "FROZEN":
        raise ContractError("Contract 已冻结，不能单独修改 AC 审批状态")
    ac = db.scalar(
        select(AcceptanceCriterion).where(
            AcceptanceCriterion.contract_id == contract.id,
            AcceptanceCriterion.ac_id == ac_id,
        )
    )
    if ac is None:
        raise ContractError(f"AC 不存在: {ac_id}")
    ac.approval_status = "APPROVED"
    ac.approved_by = int(approver_id)
    ac.approved_at = datetime.now(UTC)
    db.flush()
    return ac


def supersede_contract(db: Session, contract_id: str, *, project_id: int) -> RequirementContract:
    contract = get_contract(db, contract_id, project_id)
    if contract.status == "SUPERSEDED":
        return contract
    contract.status = "SUPERSEDED"
    db.flush()
    return contract


def update_contract(
    db: Session, contract_id: str, *, project_id: int, **fields: Any
) -> RequirementContract:
    """冻结/已批准版本不可原地更新——必须新建 revision。"""
    contract = get_contract(db, contract_id, project_id)
    if contract.status in {"FROZEN", "APPROVED"}:
        raise ContractError(
            f"Contract 状态 {contract.status} 不可原地更新，请新建 revision"
        )
    allowed = {"title", "business_goal", "actors_json", "business_rules_json", "nfr_json"}
    for key, value in fields.items():
        if key in allowed:
            setattr(contract, key, value)
    contract.revision_checksum = compute_checksum(contract, list_acs(db, contract.id))
    db.flush()
    return contract


def impact_of_revision(db: Session, contract: RequirementContract) -> dict[str, Any]:
    """新 revision 影响的 AC / Case / Workflow 范围（供 A5 使用）。"""
    from app.aiqe.models.contract import AiqeTestCase

    acs = [ac.ac_id for ac in list_acs(db, contract.id)]
    cases = list(
        db.scalars(
            select(AiqeTestCase).where(
                AiqeTestCase.contract_id == contract.id,
            )
        )
    )
    return {
        "contract_id": contract.id,
        "requirement_id": contract.requirement_id,
        "revision": contract.revision,
        "acs": acs,
        "case_ids": [case.case_id for case in cases],
    }


__all__ = [
    "PRIORITIES_REQUIRING_ORACLE",
    "SOURCE_REF_KINDS",
    "STATUSES",
    "TRANSITIONS",
    "VAGUE_TERMS",
    "ContractError",
    "InvalidSourceRef",
    "ParsedSourceRef",
    "ambiguity_scan",
    "approve_ac",
    "compute_checksum",
    "create_contract_draft",
    "get_contract",
    "impact_of_revision",
    "list_acs",
    "parse_source_ref",
    "resolve_source_ref",
    "supersede_contract",
    "transition_contract",
    "update_contract",
]
