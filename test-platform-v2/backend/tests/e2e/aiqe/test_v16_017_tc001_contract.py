"""V16-017 R1: contract freeze + V2 impact platform chain.

诚实边界：本文件只验证 Contract Service 的冻结/校验和/影响面平台行为，
**不是**产品 TC-AIQE-001（API→后台 UI→DB→前台 UI 同一 Run）的证据。
机器结果登记为 NOT_RUN 并说明原因，禁止冒充 TC-AIQE-001 PASS。
"""
from __future__ import annotations

from app.aiqe.services import contract_service
from platform_results import record_tc


def _acs(prefix: str) -> list[dict]:
    return [
        {
            "ac_id": f"{prefix}-001",
            "given": "已登录",
            "when": "收藏赛事",
            "then": ["收藏成功"],
            "priority": "P1",
            "oracle_type": "REQ",
            "oracle_ref": "PRD:favorites",
        }
    ]


def test_tc_001_contract_freeze_and_v2_impact(db_session):
    c1 = contract_service.create_contract_draft(
        db_session,
        project_id=1,
        requirement_id="favorite-match",
        title="收藏赛事",
        source_refs=["prd:favorites-v1.md#收藏赛事"],
        acceptance_criteria=_acs("V1"),
        created_by=1,
    )
    for ac in contract_service.list_acs(db_session, c1.id):
        contract_service.approve_ac(db_session, contract_id=c1.id, ac_id=ac.ac_id, project_id=1, approver_id=1)
    for target in ("REVIEW_REQUIRED", "APPROVED", "FROZEN"):
        contract_service.transition_contract(db_session, c1.id, target, project_id=1, actor_id=1)
    db_session.commit()
    checksum = c1.revision_checksum
    c2 = contract_service.create_contract_draft(
        db_session,
        project_id=1,
        requirement_id="favorite-match",
        title="收藏赛事 V2",
        source_refs=["prd:favorites-v2.md#收藏赛事"],
        acceptance_criteria=_acs("V2"),
        created_by=1,
    )
    db_session.commit()
    db_session.refresh(c1)
    assert c1.revision_checksum == checksum
    assert c2.revision == 2
    assert c2.revision_checksum != checksum
    record_tc(
        "TC-PLATFORM-010",
        status="NOT_RUN",
        blocked_reason="Contract Service 平台行为测试，无 TestRun/UI/DB 链路，不能计为产品 TC-001 运行证据",
    )
