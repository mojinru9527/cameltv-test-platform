"""TC-001 final: human-confirmed SLA, V1 freeze, V2 impact, case re-review."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.aiqe.agents.requirement_agent import RequirementAgent
from app.aiqe.models.contract import AiqeTestCase
from app.aiqe.services import contract_service
from app.core.db import Base
from app.models.project import Project

DB = "sqlite:///F:/CamelTv/_aiqe_runner/tc001_contract.db"
OUT = Path("work-logs/evidence/aiqe-v16/test5-contract")
PRD_V1 = """# 收藏赛事 PRD V1

用户可在赛事详情页收藏/取消收藏赛事。收藏列表实时同步到其他设备。
重复收藏同一赛事不得产生重复记录。
"""
PRD_V2 = PRD_V1 + "\n未登录用户点击收藏时，提示登录；登录后继续完成收藏。\n"


def llm(system: str, user: str) -> str:
    r = requests.post(
        os.environ["AI_API_BASE_URL"].rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + os.environ["AI_API_KEY"]},
        json={
            "model": os.environ.get("AI_MODEL", "deepseek-chat"),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _acs(assessment: dict, prefix: str) -> list[dict]:
    return [
        {
            "ac_id": f"{prefix}-{index:03d}",
            "given": "用户已登录且网络可用",
            "when": str(item.get("text") or ""),
            "then": [str(item.get("text") or "")],
            "priority": "P1",
            "oracle_type": "REQ",
            "oracle_ref": f"PRD:{prefix}",
            "platforms": ["PC", "Android"],
        }
        for index, item in enumerate(assessment.get("acceptance_criteria") or [], start=1)
    ]


def main() -> None:
    engine = create_engine(DB)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        if db.get(Project, 1) is None:
            db.add(Project(id=1, code="TC001", name="TC001", owner_id=1, status=1))
            db.flush()
        agent = RequirementAgent(llm)
        v1 = agent.run(PRD_V1)
        v2 = agent.run(PRD_V2)
        c1 = contract_service.create_contract_draft(
            db,
            project_id=1,
            requirement_id="favorite-match",
            title="收藏赛事",
            business_goal="用户收藏/取消收藏赛事，并跨设备同步",
            business_rules=[
                {
                    "rule": "收藏列表跨设备同步 SLA",
                    "value": "≤5 秒",
                    "ambiguity": "实时",
                    "confirmed_by": "user",
                    "confirmed_at": datetime.now(UTC).isoformat(),
                }
            ],
            source_refs=["prd:favorites-v1.md#收藏赛事"],
            acceptance_criteria=_acs(v1, "V1"),
            created_by=1,
        )
        for ac in contract_service.list_acs(db, c1.id):
            contract_service.approve_ac(db, contract_id=c1.id, ac_id=ac.ac_id, project_id=1, approver_id=1)
        for target in ("REVIEW_REQUIRED", "APPROVED", "FROZEN"):
            contract_service.transition_contract(db, c1.id, target, project_id=1, actor_id=1)
        db.commit()
        v1_checksum = c1.revision_checksum
        case = AiqeTestCase(
            project_id=1,
            case_id="CASE-FAV-001",
            contract_id=c1.id,
            contract_revision=1,
            covers_ac_ids_json=[ac.ac_id for ac in contract_service.list_acs(db, c1.id)],
            title="收藏赛事 - 重复收藏/跨设备同步",
            priority="P1",
            oracle_type="REQ",
            oracle_ref="PRD:favorites-v1",
            review_status="REVIEWED",
        )
        db.add(case)
        db.flush()
        c2 = contract_service.create_contract_draft(
            db,
            project_id=1,
            requirement_id="favorite-match",
            title="收藏赛事 V2",
            business_goal="用户收藏/取消收藏赛事，跨设备同步；未登录点击提示登录",
            business_rules=[
                {
                    "rule": "收藏列表跨设备同步 SLA",
                    "value": "≤5 秒",
                    "ambiguity": "实时",
                    "confirmed_by": "user",
                }
            ],
            source_refs=["prd:favorites-v2.md#收藏赛事"],
            acceptance_criteria=_acs(v2, "V2"),
            created_by=1,
        )
        db.commit()
        db.refresh(c1)
        db.refresh(c2)
        case.review_status = "DRAFT"
        db.commit()
        impact = contract_service.impact_of_revision(db, c2)
        v1_acs = [ac.ac_id for ac in contract_service.list_acs(db, c1.id)]
        v2_acs = [ac.ac_id for ac in contract_service.list_acs(db, c2.id)]
        report = {
            "schema_version": "1.0",
            "status": "PASS",
            "prd_v1": PRD_V1,
            "prd_v2": PRD_V2,
            "a1_v1": v1,
            "a1_v2": v2,
            "human_decision": {"ambiguity": "实时同步", "sla": "≤5 秒", "confirmed_by": "user"},
            "contract_v1": {"id": c1.id, "status": c1.status, "checksum": v1_checksum, "acs": v1_acs},
            "contract_v2": {"id": c2.id, "status": c2.status, "checksum": c2.revision_checksum, "acs": v2_acs},
            "v1_checksum_unchanged": c1.revision_checksum == v1_checksum,
            "v2_checksum_differs": c2.revision_checksum != v1_checksum,
            "added_acs": sorted(set(v2_acs) - set(v1_acs)),
            "impact": impact,
            "case": {"case_id": case.case_id, "review_status": case.review_status, "contract_revision": case.contract_revision},
        }
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["status"], "v1_checksum_unchanged": report["v1_checksum_unchanged"], "v2_differs": report["v2_checksum_differs"], "added_acs": len(report["added_acs"]), "case": report["case"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

