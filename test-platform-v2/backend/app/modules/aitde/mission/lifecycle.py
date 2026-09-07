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
from app.modules.aitde.ai_closed_loop.models import ScenarioGapCandidate
from app.modules.aitde.ai_ops.models import AIOperationRecord
from app.modules.aitde.continuous.models import (
    BuildObservation,
    ExecutionCampaign,
    QualityGateResultRecord,
)
from app.modules.aitde.contract.models import TestContract, TestContractVersion
from app.modules.aitde.contract.schemas import ContractSnapshot
from app.modules.aitde.execution.models import (
    AssertionResult,
    EvidenceArtifact,
    ExecutionRun,
    ExecutionStep,
    ReplayManifest,
)
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion
from app.modules.aitde.smart_regression.models import (
    ChangeItem,
    ChangeSet,
    ImpactAnalysisRun,
    LineageEdge,
)
from app.modules.aitde.scope.models import ScopeItem
from app.modules.aitde.sources.models import (
    MissionSourceLink,
    SourceArtifact,
    SourceFragment,
)


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


def _json_dict(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(raw: str | None) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def _source_refs_valid(raw: str | None, valid_refs: set[tuple[int, int]]) -> bool:
    try:
        refs = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return False
    if not isinstance(refs, list) or not refs:
        return False
    return all(
        isinstance(ref, dict)
        and isinstance(ref.get("artifact_id"), int)
        and isinstance(ref.get("fragment_id"), int)
        and (ref["artifact_id"], ref["fragment_id"]) in valid_refs
        for ref in refs
    )


def _contract_complete(
    version: TestContractVersion | None,
    valid_refs: set[tuple[int, int]],
) -> bool:
    if version is None or version.status != "FROZEN":
        return False
    try:
        snapshot = ContractSnapshot.model_validate_json(version.snapshot_json or "{}")
    except (TypeError, ValueError):
        return False
    references = [
        ref
        for item in [*snapshot.rules, *snapshot.required_outcomes]
        for ref in item.source_refs
    ]
    return bool(
        snapshot.rules
        and snapshot.required_outcomes
        and references
        and all(
            ref.fragment_id is not None
            and (ref.artifact_id, ref.fragment_id) in valid_refs
            for ref in references
        )
    )


def _scenario_complete(
    version: TestScenarioVersion,
    valid_refs: set[tuple[int, int]],
) -> bool:
    return bool(
        version.review_status == "APPROVED"
        and version.case_type in {"FUNCTIONAL", "API", "UI"}
        and version.requirement_role in {"NEW", "CHANGED", "IMPACTED_BASELINE"}
        and (version.module_key or "").strip()
        and (version.business_goal or "").strip()
        and _json_dict(version.given_model_json)
        and _json_dict(version.when_model_json)
        and _json_dict(version.expected_state_json)
        and _source_refs_valid(version.source_refs_json, valid_refs)
    )


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
    source_ids = [source.id for source in sources]
    fragments = (
        list(
            db.scalars(
                select(SourceFragment).where(SourceFragment.artifact_id.in_(source_ids))
            ).all()
        )
        if source_ids
        else []
    )
    fragment_count_by_source = Counter(fragment.artifact_id for fragment in fragments)
    valid_source_refs = {(fragment.artifact_id, fragment.id) for fragment in fragments}
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
    steps = (
        list(db.scalars(select(ExecutionStep).where(ExecutionStep.run_id.in_(run_ids))).all())
        if run_ids
        else []
    )
    assertions = (
        list(db.scalars(select(AssertionResult).where(AssertionResult.run_id.in_(run_ids))).all())
        if run_ids
        else []
    )
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
    replays = (
        list(db.scalars(select(ReplayManifest).where(ReplayManifest.run_id.in_(run_ids))).all())
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
    verified_evidence_by_run = Counter(
        item.run_id
        for item in evidence
        if item.integrity_status == "VERIFIED"
        and item.sanitization_status == "SANITIZED"
        and item.storage_verified_at is not None
        and bool(item.content_hash)
    )
    steps_by_run = Counter(item.run_id for item in steps)
    assertions_by_run = Counter(item.run_id for item in assertions)
    replays_by_run = Counter(item.run_id for item in replays)
    defects_by_run = Counter(item.aitde_run_id for item in defects)

    cases = []
    for scenario, version in scenario_rows:
        scenario_runs = runs_by_scenario.get(scenario.id, [])
        latest = max(scenario_runs, key=lambda run: run.id) if scenario_runs else None
        source_refs_valid = _source_refs_valid(version.source_refs_json, valid_source_refs)
        meaningful = _scenario_complete(version, valid_source_refs)
        run_complete = bool(scenario_runs) and all(
            run.runtime_status == "FINISHED"
            and run.outcome is not None
            and steps_by_run[run.id] > 0
            and assertions_by_run[run.id] > 0
            and verified_evidence_by_run[run.id] > 0
            and replays_by_run[run.id] > 0
            for run in scenario_runs
        )
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
                "source_refs_valid": source_refs_valid,
                "content_complete": meaningful,
                "run_count": len(scenario_runs),
                "latest_run_id": latest.id if latest else None,
                "latest_outcome": latest.outcome if latest else None,
                "evidence_count": sum(evidence_by_run[run.id] for run in scenario_runs),
                "verified_evidence_count": sum(
                    verified_evidence_by_run[run.id] for run in scenario_runs
                ),
                "step_count": sum(steps_by_run[run.id] for run in scenario_runs),
                "assertion_count": sum(
                    assertions_by_run[run.id] for run in scenario_runs
                ),
                "replay_count": sum(replays_by_run[run.id] for run in scenario_runs),
                "execution_complete": run_complete,
                "defect_count": sum(defects_by_run[run.id] for run in scenario_runs),
                "retest_count": sum(1 for run in scenario_runs if run.parent_run_id is not None),
                "retest_status": _retest_status(scenario_runs),
            }
        )

    case_types = Counter(case["case_type"] for case in cases)
    requirement_roles = Counter(case["requirement_role"] for case in cases)
    complete_scope = sum(
        item.review_status in {"APPROVED", "REJECTED"}
        and item.decision in {"INCLUDE", "EXCLUDE"}
        and bool((item.name or "").strip())
        and bool((item.reason or "").strip())
        and _source_refs_valid(item.source_refs_json, valid_source_refs)
        for item in scope_items
    )
    complete_cases = sum(case["content_complete"] for case in cases)
    missing_case_lanes = [
        lane for lane in ("FUNCTIONAL", "API", "UI") if case_types[lane] == 0
    ]
    executed_cases = len({run.scenario_id for run in runs if run.runtime_status == "FINISHED"})
    evidenced_cases = sum(case["execution_complete"] for case in cases)

    gate_results = list(
        db.scalars(
            select(QualityGateResultRecord)
            .where(QualityGateResultRecord.mission_id == mission.id)
            .order_by(QualityGateResultRecord.id.desc())
        ).all()
    )
    latest_gate = gate_results[0] if gate_results else None

    builds = list(
        db.scalars(select(BuildObservation).where(BuildObservation.mission_id == mission.id)).all()
    )
    campaigns = list(
        db.scalars(
            select(ExecutionCampaign).where(
                ExecutionCampaign.mission_id == mission.id,
                ExecutionCampaign.project_id == project_id,
            )
        ).all()
    )
    build_ids = {item.id for item in builds}
    campaign_ids = {item.id for item in campaigns}
    gate_checks = _json_list(latest_gate.checks_json) if latest_gate else []
    gate_pass_is_supported = bool(
        gate_checks
        and all(
            isinstance(check, dict)
            and (check.get("status") == "PASS" or check.get("pass") is True)
            for check in gate_checks
        )
    )
    gate_is_bound = bool(
        latest_gate
        and latest_gate.campaign_id in campaign_ids
        and latest_gate.build_observation_id in build_ids
        and latest_gate.result in {"PASS", "FAIL"}
        and (latest_gate.result != "PASS" or gate_pass_is_supported)
    )
    effective_acceptance = latest_gate.result if gate_is_bound else "NOT_EVALUATED"
    acceptance_done = int(gate_is_bound)
    change_sets = list(
        db.scalars(
            select(ChangeSet).where(
                ChangeSet.mission_id == mission.id,
                ChangeSet.project_id == project_id,
            )
        ).all()
    )
    change_set_ids = [item.id for item in change_sets]
    change_items = (
        list(db.scalars(select(ChangeItem).where(ChangeItem.change_set_id.in_(change_set_ids))).all())
        if change_set_ids
        else []
    )
    impact_runs = list(
        db.scalars(
            select(ImpactAnalysisRun).where(
                ImpactAnalysisRun.mission_id == mission.id,
                ImpactAnalysisRun.project_id == project_id,
            )
        ).all()
    )
    lineage_edges = list(
        db.scalars(
            select(LineageEdge).where(
                LineageEdge.mission_id == mission.id,
                LineageEdge.project_id == project_id,
            )
        ).all()
    )
    gap_candidates = list(
        db.scalars(
            select(ScenarioGapCandidate).where(ScenarioGapCandidate.mission_id == mission.id)
        ).all()
    )
    gap_analysis = db.scalar(
        select(AIOperationRecord)
        .where(
            AIOperationRecord.mission_id == mission.id,
            AIOperationRecord.project_id == project_id,
            AIOperationRecord.operation_type == "scenario:gap",
            AIOperationRecord.status == "SUCCEEDED",
        )
        .order_by(AIOperationRecord.id.desc())
        .limit(1)
    )

    stages = [
        _stage(
            "sources",
            "资料",
            len(sources),
            sum(
                source.parse_status == "PARSED" and fragment_count_by_source[source.id] > 0
                for source in sources
            ),
            "尚无带有效片段的需求资料" if not sources else "存在空片段或尚未解析的资料",
        ),
        _stage(
            "analysis",
            "需求分析",
            len(scope_items),
            complete_scope,
            "尚未形成需求范围" if not scope_items else "范围内容、评审或来源引用不完整",
        ),
        _stage(
            "contract",
            "测试契约",
            1 if contract_version else 0,
            int(_contract_complete(contract_version, valid_source_refs)),
            "测试契约为空、格式无效或尚未冻结",
        ),
        _stage(
            "cases",
            "用例设计",
            len(cases) + len(missing_case_lanes),
            complete_cases,
            (
                "尚未生成用例"
                if not cases
                else "用例内容/来源不完整"
                + (f"，缺少 {'/'.join(missing_case_lanes)} 类型" if missing_case_lanes else "")
            ),
        ),
        _stage(
            "execution",
            "执行证据",
            len(cases),
            evidenced_cases,
            "尚无逐用例执行证据"
            if not runs
            else f"{len(cases) - evidenced_cases} 条用例缺步骤、断言、已验证证据或回放",
        ),
        _stage(
            "acceptance",
            "验收结论",
            1 if latest_gate else 0,
            acceptance_done,
            "尚未形成绑定 Build 与 Campaign 的 Quality Gate 结论",
        ),
    ]

    supporting_stages = [
        _stage(
            "builds",
            "Build",
            1 if builds else 0,
            int(bool(builds)),
            "尚未采集 Build 指纹",
        ),
        _stage(
            "changes",
            "变化检测",
            1 if change_sets else 0,
            int(bool(change_sets)),
            "尚未持久化变化检测结果",
        ),
        _stage(
            "impact",
            "影响分析",
            len(change_sets),
            len({run.change_set_id for run in impact_runs if run.status == "COMPLETED"}),
            "仍有 ChangeSet 未完成影响分析",
        ),
        _stage(
            "lineage",
            "Lineage",
            1 if cases else 0,
            int(bool(cases and lineage_edges)),
            "尚未生成来源到执行的追溯链",
        ),
        _stage(
            "gaps",
            "场景缺口",
            1 if gap_analysis or gap_candidates else 0,
            int(bool(gap_analysis or gap_candidates)),
            "尚未执行场景缺口分析",
        ),
    ]

    integrity_status = (
        "COMPLETE"
        if all(stage["status"] == "COMPLETE" for stage in stages + supporting_stages)
        else "INCOMPLETE"
    )

    return {
        "mission": {
            "id": mission.id,
            "mission_type": mission.mission_type,
            "status": mission.status,
            "acceptance_status": effective_acceptance,
            "stored_acceptance_status": mission.acceptance_status,
            "acceptance_consistent": mission.acceptance_status == effective_acceptance,
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
        "supporting_stages": supporting_stages,
        "integrity_status": integrity_status,
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
            "verified_evidence": sum(verified_evidence_by_run.values()),
            "steps": len(steps),
            "assertions": len(assertions),
            "replays": len(replays),
            "defects": len(defects),
            "retests": sum(case["retest_count"] for case in cases),
            "executed_cases": executed_cases,
        },
        "cases": cases,
        "artifacts": {
            "fragments": len(fragments),
            "change_sets": len(change_sets),
            "change_items": len(change_items),
            "impact_runs": len(impact_runs),
            "lineage_edges": len(lineage_edges),
            "gap_candidates": len(gap_candidates),
            "latest_change_set_id": max(change_set_ids) if change_set_ids else None,
            "latest_impact_run_id": max((run.id for run in impact_runs), default=None),
            "latest_gate_result_id": latest_gate.id if latest_gate else None,
        },
        "gaps": [
            stage["gap"] for stage in stages + supporting_stages if stage["gap"]
        ],
    }
