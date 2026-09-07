"""Read-only Mission lifecycle projection backed by persisted test facts."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.defect import Defect
from app.models.version_task import VersionTask
from app.modules.aitde.contract.models import TestContract, TestContractVersion
from app.modules.aitde.execution.models import EvidenceArtifact, ExecutionRun
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion
from app.modules.aitde.scope.models import ScopeItem
from app.modules.aitde.sources.models import MissionSourceLink, SourceArtifact


_PHASE_LABELS = {
    "FEATURE": "需求测试",
    "VERSION": "版本回归",
    "REGRESSION": "生产回归",
}
_FAILURE_OUTCOMES = {
    "BUSINESS_FAIL",
    "AUTOMATION_FAIL",
    "DATA_FAIL",
    "ENV_FAIL",
    "ASSERTION_ERROR",
    "BLOCKED",
    "INCONCLUSIVE",
}


def _stage(key: str, label: str, total: int, completed: int, gap: str) -> dict[str, Any]:
    if total == 0:
        status = "NOT_STARTED"
    elif completed >= total:
        status = "COMPLETE"
    else:
        status = "IN_PROGRESS"
    return {
        "key": key,
        "label": label,
        "status": status,
        "total": total,
        "completed": completed,
        "gap": "" if status == "COMPLETE" else gap,
    }


def _source_ref_count(raw: str) -> int:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return 0
    return len(value) if isinstance(value, list) else 0


def _retest_status(runs: list[ExecutionRun]) -> str:
    if not any(run.outcome in _FAILURE_OUTCOMES for run in runs):
        return "NOT_REQUIRED"
    retries = [run for run in runs if run.parent_run_id is not None]
    if not retries:
        return "PENDING_RETEST"
    latest_retry = max(retries, key=lambda run: run.id)
    return "RETEST_PASSED" if latest_retry.outcome == "PASS" else "RETEST_FAILED"


def build_lifecycle(db: Session, mission_id: int, project_id: int) -> dict[str, Any]:
    mission = db.scalar(
        select(Mission).where(Mission.id == mission_id, Mission.project_id == project_id)
    )
    if mission is None:
        raise APIException(code=404, msg="任务不存在", http_status=404)

    version_task = None
    phases: list[Mission] = []
    if mission.version_task_id is not None:
        version_task = db.scalar(
            select(VersionTask).where(
                VersionTask.id == mission.version_task_id,
                VersionTask.project_id == project_id,
            )
        )
        phases = list(
            db.scalars(
                select(Mission)
                .where(
                    Mission.project_id == project_id,
                    Mission.version_task_id == mission.version_task_id,
                )
                .order_by(Mission.id.asc())
            ).all()
        )

    sources = list(
        db.scalars(
            select(SourceArtifact)
            .join(MissionSourceLink, MissionSourceLink.artifact_id == SourceArtifact.id)
            .where(
                MissionSourceLink.mission_id == mission.id,
                SourceArtifact.project_id == project_id,
            )
        ).all()
    )
    scope_items = list(
        db.scalars(select(ScopeItem).where(ScopeItem.mission_id == mission.id)).all()
    )
    contract_version = None
    if mission.current_contract_version_id:
        contract_version = db.scalar(
            select(TestContractVersion)
            .join(TestContract, TestContractVersion.contract_id == TestContract.id)
            .where(
                TestContractVersion.id == mission.current_contract_version_id,
                TestContract.mission_id == mission.id,
            )
        )
    scenario_rows = list(
        db.execute(
            select(TestScenario, TestScenarioVersion)
            .join(
                TestScenarioVersion,
                (TestScenarioVersion.scenario_id == TestScenario.id)
                & (TestScenarioVersion.version_no == TestScenario.current_version_no),
            )
            .where(
                TestScenario.mission_id == mission.id,
                TestScenario.project_id == project_id,
            )
            .order_by(TestScenario.id.asc())
        ).all()
    )
    runs = list(
        db.scalars(
            select(ExecutionRun)
            .where(
                ExecutionRun.mission_id == mission.id,
                ExecutionRun.project_id == project_id,
            )
            .order_by(ExecutionRun.id.asc())
        ).all()
    )
    run_ids = [run.id for run in runs]
    evidence = (
        list(
            db.scalars(
                select(EvidenceArtifact).where(
                    EvidenceArtifact.project_id == project_id,
                    EvidenceArtifact.run_id.in_(run_ids),
                )
            ).all()
        )
        if run_ids
        else []
    )
    defects = (
        list(
            db.scalars(
                select(Defect).where(
                    Defect.project_id == project_id,
                    Defect.aitde_run_id.in_(run_ids),
                )
            ).all()
        )
        if run_ids
        else []
    )

    runs_by_scenario: dict[int, list[ExecutionRun]] = defaultdict(list)
    for run in runs:
        runs_by_scenario[run.scenario_id].append(run)
    evidence_by_run = Counter(item.run_id for item in evidence)
    defects_by_run = Counter(item.aitde_run_id for item in defects)

    cases = []
    for scenario, version in scenario_rows:
        scenario_runs = runs_by_scenario.get(scenario.id, [])
        latest = max(scenario_runs, key=lambda run: run.id) if scenario_runs else None
        cases.append(
            {
                "scenario_id": scenario.id,
                "scenario_version_id": version.id,
                "scenario_key": scenario.scenario_key,
                "title": version.title,
                "case_type": version.case_type or "UNCLASSIFIED",
                "requirement_role": version.requirement_role or "UNCLASSIFIED",
                "module_key": version.module_key,
                "review_status": version.review_status,
                "source_ref_count": _source_ref_count(version.source_refs_json),
                "run_count": len(scenario_runs),
                "latest_run_id": latest.id if latest else None,
                "latest_outcome": latest.outcome if latest else None,
                "evidence_count": sum(evidence_by_run[run.id] for run in scenario_runs),
                "defect_count": sum(defects_by_run[run.id] for run in scenario_runs),
                "retest_count": sum(1 for run in scenario_runs if run.parent_run_id is not None),
                "retest_status": _retest_status(scenario_runs),
            }
        )

    case_types = Counter(case["case_type"] for case in cases)
    requirement_roles = Counter(case["requirement_role"] for case in cases)
    approved_scope = sum(item.review_status in {"APPROVED", "REJECTED"} for item in scope_items)
    approved_cases = sum(case["review_status"] == "APPROVED" for case in cases)
    executed_cases = len({run.scenario_id for run in runs if run.runtime_status == "FINISHED"})
    evidenced_cases = len(
        {
            run.scenario_id
            for run in runs
            if run.runtime_status == "FINISHED" and evidence_by_run[run.id] > 0
        }
    )
    acceptance_done = int(
        mission.acceptance_status in {"PASS", "FAIL"} and executed_cases > 0
    )

    stages = [
        _stage(
            "sources",
            "资料",
            len(sources),
            sum(source.parse_status == "PARSED" for source in sources),
            "尚无已解析需求资料" if not sources else "存在尚未解析的资料",
        ),
        _stage(
            "analysis",
            "需求分析",
            len(scope_items),
            approved_scope,
            "尚未形成需求范围" if not scope_items else "存在尚未评审的范围项",
        ),
        _stage(
            "contract",
            "测试契约",
            1 if contract_version else 0,
            int(bool(contract_version and contract_version.status == "FROZEN")),
            "尚未冻结测试契约",
        ),
        _stage(
            "cases",
            "用例设计",
            len(cases),
            approved_cases,
            "尚未生成用例" if not cases else "存在尚未批准的用例",
        ),
        _stage(
            "execution",
            "执行证据",
            len(cases),
            evidenced_cases,
            "尚无逐用例执行证据" if not runs else f"{len(cases) - evidenced_cases} 条用例尚无证据",
        ),
        _stage(
            "acceptance",
            "验收结论",
            1 if executed_cases else 0,
            acceptance_done,
            "尚未形成基于执行证据的验收结论",
        ),
    ]

    return {
        "mission": {
            "id": mission.id,
            "mission_type": mission.mission_type,
            "status": mission.status,
            "acceptance_status": mission.acceptance_status,
            "version_task_id": mission.version_task_id,
        },
        "version_task": (
            {
                "id": version_task.id,
                "title": version_task.title,
                "version": version_task.version,
                "status": version_task.status,
            }
            if version_task
            else None
        ),
        "phases": [
            {
                "mission_id": phase.id,
                "mission_type": phase.mission_type,
                "label": _PHASE_LABELS.get(phase.mission_type, phase.mission_type),
                "status": phase.status,
                "is_current": phase.id == mission.id,
            }
            for phase in phases
        ],
        "stages": stages,
        "coverage": {
            "case_types": {
                key: case_types[key]
                for key in ("FUNCTIONAL", "API", "UI", "UNCLASSIFIED")
            },
            "requirement_roles": {
                key: requirement_roles[key]
                for key in ("NEW", "CHANGED", "IMPACTED_BASELINE", "UNCLASSIFIED")
            },
        },
        "totals": {
            "cases": len(cases),
            "runs": len(runs),
            "evidence": len(evidence),
            "defects": len(defects),
            "retests": sum(case["retest_count"] for case in cases),
            "executed_cases": executed_cases,
        },
        "cases": cases,
        "gaps": [stage["gap"] for stage in stages if stage["gap"]],
    }
