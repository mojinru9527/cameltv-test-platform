"""AUD-015：结构化 TestCase（automation grade A–D / AC 覆盖 / Oracle / 去重）。

v1.5 §03 AUD-015：

- A 级：输入/数据/Driver/动作/断言/Oracle/清理/权限都明确，可自动生成 Workflow Draft；
- B 级：少量环境/fixture/定位器需要补齐；
- C 级：业务预期需人工确认，只能手工执行或等待审批；
- D 级：需求模糊、无 Oracle、依赖无法满足，**禁止自动执行**；
- 缺 ``assertions``/``oracle_ref``/平台绑定的 P0 不能是 A/B 级；
- 每条 AC 输出未覆盖/部分覆盖/已覆盖；重复生成不产生同逻辑冗余 Case。
"""
from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.contract import AcceptanceCriterion, AiqeTestCase, RequirementContract
from app.aiqe.services.contract_service import ContractError, get_contract, list_acs

GRADES: tuple[str, ...] = ("A", "B", "C", "D")
EXECUTABLE_GRADES: frozenset[str] = frozenset({"A", "B"})
REVIEW_STATUSES: tuple[str, ...] = ("DRAFT", "REVIEWED", "REJECTED")


class TestCaseError(ValueError):
    pass


def _has_assertions(steps: Sequence[Mapping[str, Any]]) -> bool:
    for step in steps:
        if isinstance(step, Mapping) and step.get("assertions"):
            return True
    return False


def _all_steps_structured(steps: Sequence[Mapping[str, Any]]) -> bool:
    if not steps:
        return False
    for step in steps:
        if not isinstance(step, Mapping):
            return False
        if not str(step.get("driver") or "").strip():
            return False
        if not str(step.get("action") or "").strip():
            return False
    return True


def grade_case(payload: Mapping[str, Any]) -> tuple[str, list[str]]:
    """返回 ``(grade, reasons)``；D 级禁止进入自动执行。"""
    reasons: list[str] = []
    steps = list(payload.get("steps") or [])
    platforms = [str(item) for item in (payload.get("platform_targets") or []) if str(item)]
    oracle_ref = str(payload.get("oracle_ref") or "")
    priority = str(payload.get("priority") or "P2").upper()
    cleanup = list(payload.get("cleanup") or [])
    fixtures = list(payload.get("fixtures") or [])

    if not steps:
        return "D", ["NO_STEPS"]
    if not _all_steps_structured(steps):
        return "D", ["STEP_NOT_STRUCTURED"]
    if not _has_assertions(steps) and not payload.get("assertions"):
        reasons.append("NO_ASSERTIONS")
    if not oracle_ref:
        reasons.append("NO_ORACLE")
    if not platforms:
        reasons.append("NO_PLATFORM_BINDING")
    if reasons and priority in {"P0", "P1"}:
        return "D", [*reasons, "P0_P1_REQUIRES_ASSERTION_ORACLE_PLATFORM"]

    if reasons:
        # P2/P3 缺断言/Oracle 只能人工确认后执行
        return "C", [*reasons, "BUSINESS_EXPECTATION_NEEDS_HUMAN"]

    if not cleanup or not fixtures or not payload.get("preconditions"):
        if not cleanup:
            reasons.append("NO_CLEANUP")
        if not fixtures:
            reasons.append("NO_FIXTURE")
        if not payload.get("preconditions"):
            reasons.append("NO_PRECONDITION")
        return "B", reasons

    return "A", reasons


def _dedupe_key(payload: Mapping[str, Any]) -> str:
    parts = {
        "title": str(payload.get("title") or "").strip().lower(),
        "platforms": sorted(str(item) for item in (payload.get("platform_targets") or [])),
        "acs": sorted(str(item) for item in (payload.get("covers_ac_ids") or [])),
        "priority": str(payload.get("priority") or "").upper(),
    }
    encoded = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _assert_contract_revision(
    db: Session, contract_id: str | None, revision: int | None, priority: str
) -> RequirementContract | None:
    if not contract_id:
        if priority in {"P0", "P1"}:
            raise TestCaseError("P0/P1 Case 必须绑定已批准的 Contract revision")
        return None
    contract = db.get(RequirementContract, str(contract_id))
    if contract is None:
        raise TestCaseError(f"Contract 不存在: {contract_id}")
    if revision is not None and int(revision) != int(contract.revision):
        raise TestCaseError(
            f"Contract revision 不匹配：期望 {contract.revision}，实际 {revision}"
        )
    if priority in {"P0", "P1"} and contract.status not in {"APPROVED", "FROZEN"}:
        raise TestCaseError(
            f"P0/P1 Case 需要 APPROVED/FROZEN Contract，当前 {contract.status}"
        )
    return contract


def _assert_ac_coverage(
    db: Session, contract: RequirementContract | None, covers: list[str]
) -> None:
    if contract is None:
        return
    known = {ac.ac_id for ac in list_acs(db, contract.id)}
    unknown = set(covers) - known
    if unknown:
        raise TestCaseError(f"覆盖了不存在的 AC: {sorted(unknown)}")


def create_case_draft(
    db: Session,
    *,
    project_id: int,
    payload: Mapping[str, Any],
    case_id: str | None = None,
) -> tuple[AiqeTestCase, bool]:
    """创建（或按语义去重命中）结构化 Case；返回 ``(row, created)``。"""
    priority = str(payload.get("priority") or "P2").upper()
    contract = _assert_contract_revision(
        db, payload.get("contract_id"), payload.get("contract_revision"), priority
    )
    covers = [str(item) for item in (payload.get("covers_ac_ids") or [])]
    _assert_ac_coverage(db, contract, covers)
    grade, _reasons = grade_case(payload)

    dedupe = _dedupe_key(payload)
    existing = db.scalar(
        select(AiqeTestCase).where(
            AiqeTestCase.project_id == int(project_id),
            AiqeTestCase.dedupe_key == dedupe,
        )
    )
    if existing is not None:
        return existing, False

    row = AiqeTestCase(
        project_id=int(project_id),
        case_id=case_id or str(payload.get("case_id") or f"TC-{uuid.uuid4().hex[:8]}"),
        scenario_id=str(payload.get("scenario_id") or ""),
        contract_id=contract.id if contract is not None else None,
        contract_revision=contract.revision if contract is not None else None,
        covers_ac_ids_json=covers,
        title=str(payload.get("title") or "")[:300],
        priority=priority,
        preconditions_json=list(payload.get("preconditions") or []),
        fixtures_json=list(payload.get("fixtures") or []),
        platform_targets_json=[str(item) for item in (payload.get("platform_targets") or [])],
        steps_json=list(payload.get("steps") or []),
        cleanup_json=list(payload.get("cleanup") or []),
        oracle_type=str(payload.get("oracle_type") or ""),
        oracle_ref=str(payload.get("oracle_ref") or ""),
        automation_grade=grade,
        review_status="DRAFT",
        dedupe_key=dedupe,
    )
    db.add(row)
    db.flush()
    return row, True


def review_case(
    db: Session, *, project_id: int, case_id: str, decision: str, reviewer_id: int
) -> AiqeTestCase:
    row = db.scalar(
        select(AiqeTestCase).where(
            AiqeTestCase.project_id == int(project_id), AiqeTestCase.case_id == case_id
        )
    )
    if row is None:
        raise TestCaseError(f"Case 不存在: {case_id}")
    decision = str(decision or "").upper()
    if decision not in {"APPROVED", "REJECTED"}:
        raise TestCaseError("decision 只能是 APPROVED/REJECTED")
    if decision == "APPROVED" and row.automation_grade == "D":
        raise TestCaseError("D 级 Case 禁止进入自动执行，不能批准")
    row.review_status = "REVIEWED" if decision == "APPROVED" else "REJECTED"
    del reviewer_id
    db.flush()
    return row


def assert_executable(db: Session, *, project_id: int, case_id: str) -> AiqeTestCase:
    row = db.scalar(
        select(AiqeTestCase).where(
            AiqeTestCase.project_id == int(project_id), AiqeTestCase.case_id == case_id
        )
    )
    if row is None:
        raise TestCaseError(f"Case 不存在: {case_id}")
    if row.automation_grade not in EXECUTABLE_GRADES:
        raise TestCaseError(f"{row.automation_grade} 级 Case 禁止自动执行")
    if row.review_status != "REVIEWED":
        raise TestCaseError("Case 未经测试设计审核，禁止自动执行")
    return row


def coverage_report(db: Session, *, contract_id: str, project_id: int) -> dict[str, str]:
    """每条 AC 输出 UNCOVERED / PARTIAL / COVERED。"""
    contract = get_contract(db, contract_id, project_id)
    acs: list[AcceptanceCriterion] = list_acs(db, contract.id)
    cases = list(
        db.scalars(
            select(AiqeTestCase).where(
                AiqeTestCase.contract_id == contract.id,
                AiqeTestCase.contract_revision == contract.revision,
            )
        )
    )
    report: dict[str, str] = {}
    for ac in acs:
        covering = [case for case in cases if ac.ac_id in (case.covers_ac_ids_json or [])]
        executable = [case for case in covering if case.automation_grade in EXECUTABLE_GRADES]
        reviewed = [case for case in executable if case.review_status == "REVIEWED"]
        if not covering:
            report[ac.ac_id] = "UNCOVERED"
        elif reviewed:
            report[ac.ac_id] = "COVERED"
        else:
            report[ac.ac_id] = "PARTIAL"
    return report


def assert_no_uncovered_p0(db: Session, *, contract_id: str, project_id: int) -> None:
    contract = get_contract(db, contract_id, project_id)
    report = coverage_report(db, contract_id=contract.id, project_id=project_id)
    p0 = [ac.ac_id for ac in list_acs(db, contract.id) if ac.priority == "P0"]
    uncovered = [ac_id for ac_id in p0 if report.get(ac_id) != "COVERED"]
    if uncovered:
        raise ContractError(f"P0 AC 未完全覆盖，禁止进入自动执行: {uncovered}")


__all__ = [
    "EXECUTABLE_GRADES",
    "GRADES",
    "REVIEW_STATUSES",
    "TestCaseError",
    "assert_executable",
    "assert_no_uncovered_p0",
    "coverage_report",
    "create_case_draft",
    "grade_case",
    "review_case",
]
