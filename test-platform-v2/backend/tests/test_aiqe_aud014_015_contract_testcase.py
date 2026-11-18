"""AUD-014 / AUD-015：Requirement Contract 与结构化 TestCase 验收测试。

对应 v1.5 §03 AUD-014/015「验收」：
- 无来源的 P0 AC 阻止冻结；不存在的 source ref 被拒绝；
- 文档修订生成新 revision，旧 revision 不变；冻结后不可原地更新；
- 缺 assertions/oracle_ref/platform 的 P0 不能是 A/B 级；
- 每条 AC 输出 UNCOVERED/PARTIAL/COVERED；重复生成不产生冗余 Case。
"""
from __future__ import annotations

import pytest

from app.aiqe.models.contract import AiqeTestCase, RequirementContract
from app.aiqe.services.contract_service import (
    ContractError,
    InvalidSourceRef,
    ambiguity_scan,
    approve_ac,
    create_contract_draft,
    get_contract,
    list_acs,
    parse_source_ref,
    resolve_source_ref,
    supersede_contract,
    transition_contract,
    update_contract,
)
from app.aiqe.services.testcase_service import (
    TestCaseError,
    assert_executable,
    assert_no_uncovered_p0,
    coverage_report,
    create_case_draft,
    grade_case,
    review_case,
)
from app.models.defect import Defect


def _defect(db, *, project_id: int = 1) -> Defect:
    row = Defect(project_id=project_id, title="历史缺陷", severity="P1")
    db.add(row)
    db.commit()
    return row


def _ac(ac_id="AC-001", *, priority="P0", oracle=True):
    return {
        "ac_id": ac_id,
        "given": "管理员已登录",
        "when": "发布会话",
        "then": ["用户端显示直播入口"],
        "priority": priority,
        "oracle_type": "approved_product_rule" if oracle else "",
        "oracle_ref": "PRD-SPORT-1#直播" if oracle else "",
        "platforms": ["web_desktop", "mobile_web"],
    }


def _contract(db, *, requirement="REQ-SPORT-001", acs=None, refs=("prd:SPORT.md#直播",)):
    return create_contract_draft(
        db,
        project_id=1,
        requirement_id=requirement,
        title="赛事发布后用户端可观看",
        business_goal="发布即播",
        source_refs=list(refs),
        acceptance_criteria=acs or [_ac()],
    )


# ── 1. 来源引用 ─────────────────────────────────────────
def test_source_ref_parsing_and_kinds():
    assert parse_source_ref("prd:spec.md#直播").detail["anchor"] == "直播"
    assert parse_source_ref("openapi:/matches:post").detail["method"] == "POST"
    with pytest.raises(InvalidSourceRef):
        parse_source_ref("https://evil.example/x")
    with pytest.raises(InvalidSourceRef):
        parse_source_ref("openapi:/matches")  # 缺 method


def test_bug_source_ref_must_exist_in_project(db_session):
    defect = _defect(db_session)
    resolved = resolve_source_ref(db_session, project_id=1, ref=f"bug:{defect.id}")
    assert resolved.kind == "bug"
    with pytest.raises(InvalidSourceRef):
        resolve_source_ref(db_session, project_id=1, ref="bug:9999")
    with pytest.raises(InvalidSourceRef):
        resolve_source_ref(db_session, project_id=2, ref=f"bug:{defect.id}")


def test_contract_rejects_invalid_source_ref(db_session):
    with pytest.raises(InvalidSourceRef):
        _contract(db_session, refs=("bug:424242",))


def test_ambiguity_scan_flags_vague_terms():
    found = ambiguity_scan("比赛必须立即开始并保持稳定")
    terms = {item["term"] for item in found}
    assert {"立即", "稳定"} <= terms
    assert all(item["action"] == "ASK_METRIC_OR_SLA" for item in found)


# ── 2. 版本 / 状态机 / 冻结 ──────────────────────────────
def test_revision_increments_and_checksum_recorded(db_session):
    first = _contract(db_session)
    assert first.revision == 1
    assert first.revision_checksum.startswith("sha256:")
    assert first.status == "DRAFT"
    second = _contract(db_session)
    assert second.revision == 2
    db_session.expire_all()
    assert get_contract(db_session, first.id, 1).revision_checksum == first.revision_checksum


def test_p0_without_oracle_cannot_be_approved(db_session):
    contract = _contract(db_session, acs=[_ac(oracle=False)])
    transition_contract(db_session, contract.id, "REVIEW_REQUIRED", project_id=1)
    with pytest.raises(ContractError):
        transition_contract(db_session, contract.id, "APPROVED", project_id=1)


def test_full_status_machine_and_freeze_immutability(db_session):
    contract = _contract(db_session)
    transition_contract(db_session, contract.id, "REVIEW_REQUIRED", project_id=1)
    approve_ac(db_session, contract_id=contract.id, ac_id="AC-001", project_id=1, approver_id=7)
    transition_contract(db_session, contract.id, "APPROVED", project_id=1, actor_id=7)
    transition_contract(db_session, contract.id, "FROZEN", project_id=1, actor_id=7)
    db_session.expire_all()
    frozen = get_contract(db_session, contract.id, 1)
    assert frozen.status == "FROZEN"
    assert frozen.frozen_at is not None

    with pytest.raises(ContractError):
        update_contract(db_session, contract.id, project_id=1, title="改名")
    with pytest.raises(ContractError):
        approve_ac(db_session, contract_id=contract.id, ac_id="AC-001", project_id=1, approver_id=7)
    with pytest.raises(ContractError):
        transition_contract(db_session, contract.id, "APPROVED", project_id=1)

    supersede_contract(db_session, contract.id, project_id=1)
    assert get_contract(db_session, contract.id, 1).status == "SUPERSEDED"


def test_transition_rejects_illegal_jump(db_session):
    contract = _contract(db_session)
    with pytest.raises(ContractError):
        transition_contract(db_session, contract.id, "FROZEN", project_id=1)


def test_draft_can_be_updated_before_approval(db_session):
    contract = _contract(db_session)
    updated = update_contract(
        db_session, contract.id, project_id=1, title="新标题", business_goal="新目标"
    )
    assert updated.title == "新标题"
    assert updated.revision_checksum.startswith("sha256:")


# ── 3. Automation Grade ─────────────────────────────────
def _case_payload(**overrides):
    payload = {
        "title": "直播入口可见",
        "priority": "P0",
        "platform_targets": ["web_desktop"],
        "oracle_type": "requirement_ac",
        "oracle_ref": "AC-001",
        "preconditions": ["已发布赛事"],
        "fixtures": ["match-1"],
        "cleanup": ["删除 fixture"],
        "steps": [
            {
                "step_id": "S1",
                "driver": "playwright",
                "action": "open",
                "assertions": [{"operator": "exists", "expected": True}],
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_grade_matrix():
    assert grade_case(_case_payload())[0] == "A"
    assert grade_case(_case_payload(cleanup=[]))[0] == "B"
    assert grade_case(_case_payload(priority="P2", oracle_ref=""))[0] == "C"
    assert grade_case(_case_payload(oracle_ref=""))[0] == "D"
    assert grade_case(_case_payload(platform_targets=[]))[0] == "D"
    assert grade_case(_case_payload(steps=[]))[0] == "D"
    assert grade_case(_case_payload(steps=[{"step_id": "S1", "action": "open"}]))[0] == "D"


# ── 4. Case 创建 / 去重 / 审核 / 覆盖 ────────────────────
def test_p0_case_requires_approved_contract(db_session):
    contract = _contract(db_session)
    payload = _case_payload()
    payload["contract_id"] = contract.id
    payload["contract_revision"] = contract.revision
    with pytest.raises(TestCaseError):
        create_case_draft(db_session, project_id=1, payload=payload)

    transition_contract(db_session, contract.id, "REVIEW_REQUIRED", project_id=1)
    transition_contract(db_session, contract.id, "APPROVED", project_id=1, actor_id=7)
    row, created = create_case_draft(db_session, project_id=1, payload=payload)
    assert created is True
    assert row.automation_grade == "A"
    assert row.contract_revision == contract.revision


def test_case_rejects_unknown_ac_coverage(db_session):
    contract = _contract(db_session)
    payload = _case_payload(covers_ac_ids=["AC-999"], priority="P2")
    payload["contract_id"] = contract.id
    with pytest.raises(TestCaseError):
        create_case_draft(db_session, project_id=1, payload=payload)


def test_duplicate_case_is_deduped(db_session):
    payload = _case_payload(priority="P2", covers_ac_ids=["AC-001"])
    first, created = create_case_draft(db_session, project_id=1, payload=payload)
    second, created_again = create_case_draft(db_session, project_id=1, payload=payload)
    assert created is True and created_again is False
    assert first.id == second.id
    assert db_session.query(AiqeTestCase).count() == 1


def test_review_gate_and_execution_guard(db_session):
    payload = _case_payload(priority="P2")
    row, _ = create_case_draft(db_session, project_id=1, payload=payload)
    with pytest.raises(TestCaseError):
        assert_executable(db_session, project_id=1, case_id=row.case_id)
    review_case(db_session, project_id=1, case_id=row.case_id, decision="APPROVED", reviewer_id=3)
    assert assert_executable(db_session, project_id=1, case_id=row.case_id).case_id == row.case_id

    grade_d_payload = _case_payload(priority="P2", steps=[])
    grade_d, _ = create_case_draft(
        db_session, project_id=1, payload={**grade_d_payload, "title": "D 级"}
    )
    assert grade_d.automation_grade == "D"
    with pytest.raises(TestCaseError):
        review_case(
            db_session, project_id=1, case_id=grade_d.case_id, decision="APPROVED", reviewer_id=3
        )


def test_coverage_report_states(db_session):
    contract = _contract(db_session, acs=[_ac("AC-001"), _ac("AC-002")])
    assert set(acs.ac_id for acs in list_acs(db_session, contract.id)) == {"AC-001", "AC-002"}
    transition_contract(db_session, contract.id, "REVIEW_REQUIRED", project_id=1)
    transition_contract(db_session, contract.id, "APPROVED", project_id=1, actor_id=1)

    report = coverage_report(db_session, contract_id=contract.id, project_id=1)
    assert report == {"AC-001": "UNCOVERED", "AC-002": "UNCOVERED"}

    payload = _case_payload(covers_ac_ids=["AC-001"])
    payload["contract_id"] = contract.id
    payload["contract_revision"] = contract.revision
    row, _ = create_case_draft(db_session, project_id=1, payload=payload)
    report = coverage_report(db_session, contract_id=contract.id, project_id=1)
    assert report["AC-001"] == "PARTIAL"
    assert report["AC-002"] == "UNCOVERED"

    review_case(db_session, project_id=1, case_id=row.case_id, decision="APPROVED", reviewer_id=1)
    report = coverage_report(db_session, contract_id=contract.id, project_id=1)
    assert report["AC-001"] == "COVERED"
    with pytest.raises(ContractError):
        assert_no_uncovered_p0(db_session, contract_id=contract.id, project_id=1)
