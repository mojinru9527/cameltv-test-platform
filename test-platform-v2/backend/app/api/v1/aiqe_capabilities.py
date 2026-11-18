"""AUD-014/015/017/018/019/020/013：v1.5 §06 目标契约的 REST 面。

所有路由都复用已交付的 service（不新增业务逻辑），并遵守统一的：
project scope（`current.project_id`）、RBAC（`menu:aiqe_runs` / `defect:update`）、
错误映射（400/403/404/422）、以及"前端不得自报事实"的约束。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services import (
    benchmark_service,
    contract_service,
    impact_service,
    noise_intelligence,
    platform_binding_service,
    regression_terminal,
    testcase_service,
    triage_service,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe", tags=["AIQE Capabilities"])

_console = require_permission("menu:aiqe_runs")
_edit = require_permission("defect:update")


def _bad(message: str, status: int = 400) -> APIException:
    return APIException(code=status, msg=message, http_status=status)


# ── Contracts (AUD-014) ─────────────────────────────────
class ContractIn(BaseModel):
    requirement_id: str = Field(min_length=1, max_length=80)
    title: str = Field(default="", max_length=300)
    business_goal: str = ""
    actors: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    acceptance_criteria: list[dict[str, Any]] = Field(default_factory=list)


class TransitionIn(BaseModel):
    target: str = Field(min_length=1, max_length=24)


class ApproveAcIn(BaseModel):
    ac_id: str = Field(min_length=1, max_length=40)


@router.post("/contracts", response_model=R[dict], summary="创建 Requirement Contract Draft")
def create_contract_api(
    body: ContractIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        contract = contract_service.create_contract_draft(
            db,
            project_id=current.project_id or 0,
            requirement_id=body.requirement_id,
            title=body.title,
            business_goal=body.business_goal,
            actors=body.actors,
            source_refs=body.source_refs,
            acceptance_criteria=body.acceptance_criteria,
            created_by=getattr(current.user, "id", None),
        )
    except contract_service.InvalidSourceRef as exc:
        db.rollback()
        raise _bad(str(exc), 422) from None
    except contract_service.ContractError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_contract_out(db, contract))


@router.get("/contracts", response_model=R[dict], summary="Contract 列表（项目作用域）")
def list_contracts_api(
    requirement_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select

    from app.aiqe.models.contract import RequirementContract

    stmt = select(RequirementContract).where(
        RequirementContract.project_id == int(current.project_id or 0)
    )
    if requirement_id:
        stmt = stmt.where(RequirementContract.requirement_id == requirement_id)
    if status:
        stmt = stmt.where(RequirementContract.status == status.upper())
    rows = list(
        db.scalars(
            stmt.order_by(RequirementContract.created_at.desc()).limit(min(max(limit, 1), 200))
        )
    )
    return R.ok(
        {
            "items": [
                {
                    "id": row.id,
                    "requirement_id": row.requirement_id,
                    "revision": row.revision,
                    "title": row.title,
                    "status": row.status,
                    "revision_checksum": row.revision_checksum,
                    "created_at": row.created_at,
                }
                for row in rows
            ],
            "total": len(rows),
        }
    )


@router.get("/contracts/{contract_id}", response_model=R[dict], summary="Contract 详情")
def get_contract_api(
    contract_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        contract = contract_service.get_contract(db, contract_id, current.project_id or 0)
    except contract_service.ContractError as exc:
        raise _bad(str(exc), 404) from None
    return R.ok(_contract_out(db, contract))


@router.post(
    "/contracts/{contract_id}/transition", response_model=R[dict], summary="Contract 状态迁移"
)
def transition_contract_api(
    contract_id: str,
    body: TransitionIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        contract = contract_service.transition_contract(
            db,
            contract_id,
            body.target,
            project_id=current.project_id or 0,
            actor_id=getattr(current.user, "id", None),
        )
    except contract_service.ContractError as exc:
        db.rollback()
        message = str(exc)
        raise _bad(message, 404 if "不存在" in message else 400) from None
    db.commit()
    return R.ok(_contract_out(db, contract))


@router.post(
    "/contracts/{contract_id}/approve-ac", response_model=R[dict], summary="人工批准 AC"
)
def approve_ac_api(
    contract_id: str,
    body: ApproveAcIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        ac = contract_service.approve_ac(
            db,
            contract_id=contract_id,
            ac_id=body.ac_id,
            project_id=current.project_id or 0,
            approver_id=getattr(current.user, "id", 0) or 0,
        )
    except contract_service.ContractError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(
        {
            "contract_id": contract_id,
            "ac_id": ac.ac_id,
            "approval_status": ac.approval_status,
            "approved_by": ac.approved_by,
        }
    )


@router.get(
    "/contracts/{contract_id}/coverage", response_model=R[dict], summary="AC 覆盖报表（AUD-015）"
)
def contract_coverage_api(
    contract_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        report = testcase_service.coverage_report(
            db, contract_id=contract_id, project_id=current.project_id or 0
        )
    except contract_service.ContractError as exc:
        raise _bad(str(exc), 404) from None
    return R.ok(
        {
            "contract_id": contract_id,
            "coverage": report,
            "uncovered": [key for key, value in report.items() if value == "UNCOVERED"],
            "partial": [key for key, value in report.items() if value == "PARTIAL"],
        }
    )


def _contract_out(db: Session, contract) -> dict:
    acs = contract_service.list_acs(db, contract.id)
    return {
        "id": contract.id,
        "project_id": contract.project_id,
        "requirement_id": contract.requirement_id,
        "revision": contract.revision,
        "title": contract.title,
        "status": contract.status,
        "revision_checksum": contract.revision_checksum,
        "source_refs": contract.source_refs_json or [],
        "ambiguities": contract.ambiguities_json or [],
        "approved_by": contract.approved_by,
        "frozen_at": contract.frozen_at,
        "acceptance_criteria": [
            {
                "ac_id": ac.ac_id,
                "priority": ac.priority,
                "oracle_type": ac.oracle_type,
                "oracle_ref": ac.oracle_ref,
                "platforms": ac.platforms_json or [],
                "approval_status": ac.approval_status,
            }
            for ac in acs
        ],
    }


# ── Test Cases (AUD-015) ────────────────────────────────
class CaseIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    priority: str = Field(default="P2", max_length=4)
    contract_id: str | None = None
    contract_revision: int | None = None
    covers_ac_ids: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)
    platform_targets: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    cleanup: list[str] = Field(default_factory=list)
    oracle_type: str = ""
    oracle_ref: str = ""
    scenario_id: str = ""


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")


@router.post("/cases", response_model=R[dict], summary="创建结构化 Case Draft")
def create_case_api(
    body: CaseIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        row, created = testcase_service.create_case_draft(
            db, project_id=current.project_id or 0, payload=body.model_dump()
        )
    except (testcase_service.TestCaseError, contract_service.ContractError) as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok({**_case_out(row), "created": created})


@router.get("/cases", response_model=R[dict], summary="结构化 Case 列表")
def list_cases_api(
    contract_id: str | None = None,
    review_status: str | None = None,
    priority: str | None = None,
    limit: int = 100,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select

    from app.aiqe.models.contract import AiqeTestCase

    stmt = select(AiqeTestCase).where(
        AiqeTestCase.project_id == int(current.project_id or 0)
    )
    if contract_id:
        stmt = stmt.where(AiqeTestCase.contract_id == contract_id)
    if review_status:
        stmt = stmt.where(AiqeTestCase.review_status == review_status.upper())
    if priority:
        stmt = stmt.where(AiqeTestCase.priority == priority.upper())
    rows = list(
        db.scalars(stmt.order_by(AiqeTestCase.created_at.desc()).limit(min(max(limit, 1), 200)))
    )
    return R.ok({"items": [_case_out(row) for row in rows], "total": len(rows)})


@router.post("/cases/{case_id}/review", response_model=R[dict], summary="测试设计审核")
def review_case_api(
    case_id: str,
    body: ReviewIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = testcase_service.review_case(
            db,
            project_id=current.project_id or 0,
            case_id=case_id,
            decision=body.decision,
            reviewer_id=getattr(current.user, "id", 0) or 0,
        )
    except testcase_service.TestCaseError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_case_out(row))


def _case_out(row) -> dict:
    return {
        "case_id": row.case_id,
        "title": row.title,
        "priority": row.priority,
        "automation_grade": row.automation_grade,
        "review_status": row.review_status,
        "contract_id": row.contract_id,
        "contract_revision": row.contract_revision,
        "covers_ac_ids": row.covers_ac_ids_json or [],
        "platform_targets": row.platform_targets_json or [],
        "oracle_ref": row.oracle_ref,
    }


# ── Experiments (AUD-004) ───────────────────────────────
class ExperimentIn(BaseModel):
    experiment_key: str = Field(min_length=2, max_length=2)
    change: dict[str, str]
    idempotency_key: str = Field(min_length=1, max_length=128)
    hypothesis_id: str | None = None
    profile_id: str | None = None


@router.post(
    "/runs/{run_id}/experiments", response_model=R[dict], summary="创建反事实实验（E1–E6）"
)
def create_experiment_api(
    run_id: str,
    body: ExperimentIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = triage_service.create_experiment(
            db,
            experiment_key=body.experiment_key,
            change=body.change,
            idempotency_key=body.idempotency_key,
            baseline_run_id=run_id,
            hypothesis_id=body.hypothesis_id,
            profile_id=body.profile_id,
            triage_case_id=None,
        )
    except triage_service.ExperimentError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_experiment_out(row))


@router.post(
    "/experiments/{experiment_id}/launch", response_model=R[dict], summary="创建真实验证 Run"
)
def launch_experiment_api(
    experiment_id: str,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = triage_service.launch_experiment(db, experiment_id)
    except triage_service.ExperimentError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_experiment_out(row))


@router.post(
    "/experiments/{experiment_id}/sync", response_model=R[dict], summary="按验证 Run 终态收敛实验"
)
def sync_experiment_api(
    experiment_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        row = triage_service.sync_experiment_result(db, experiment_id)
    except triage_service.ExperimentError as exc:
        raise _bad(str(exc), 404) from None
    db.commit()
    return R.ok(_experiment_out(row))


def _experiment_out(row) -> dict:
    return {
        "id": row.id,
        "experiment_key": row.experiment_key,
        "changed_dimension": row.changed_dimension,
        "changed_value": row.changed_value,
        "status": row.status,
        "baseline_run_id": row.baseline_run_id,
        "verification_run_id": row.verification_run_id,
        "snapshot_diff": row.snapshot_diff_json,
        "experiment_result": row.experiment_result,
        "error_code": row.error_code,
    }


# ── Triage / Observations (AUD-019) ─────────────────────
class DetectIn(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    node_run_id: str | None = None


@router.post(
    "/runs/{run_id}/observations", response_model=R[dict], summary="运行干扰检测并落库（AUD-019）"
)
def detect_observations_api(
    run_id: str,
    body: DetectIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    detections = noise_intelligence.detect_categories(body.payload)
    rows = noise_intelligence.persist_observations(
        db,
        project_id=current.project_id or 0,
        run_id=run_id,
        node_run_id=body.node_run_id,
        detections=detections,
    )
    db.commit()
    return R.ok(
        {
            "run_id": run_id,
            "items": [
                {
                    "id": row.id,
                    "detector_key": row.detector_key,
                    "category": row.category,
                    "severity": row.severity,
                    "recommended_experiment": row.recommended_experiment,
                }
                for row in rows
            ],
        }
    )


@router.get("/runs/{run_id}/observations", response_model=R[dict], summary="干扰观测列表")
def list_observations_api(
    run_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    rows = noise_intelligence.list_observations(
        db, project_id=current.project_id or 0, run_id=run_id
    )
    return R.ok(
        {
            "items": [
                {
                    "id": row.id,
                    "detector_key": row.detector_key,
                    "category": row.category,
                    "severity": row.severity,
                    "window_start": row.window_start,
                    "window_end": row.window_end,
                    "evidence_refs": row.evidence_refs_json or [],
                    "recommended_experiment": row.recommended_experiment,
                }
                for row in rows
            ]
        }
    )


class TriageTransitionIn(BaseModel):
    target: str = Field(min_length=1, max_length=32)


@router.post("/runs/{run_id}/triage", response_model=R[dict], summary="创建 TriageCase")
def create_triage_api(
    run_id: str,
    node_run_id: str | None = None,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    row = noise_intelligence.create_triage_case(
        db, project_id=current.project_id or 0, run_id=run_id, node_run_id=node_run_id
    )
    db.commit()
    return R.ok({"id": row.id, "run_id": row.run_id, "status": row.status})


@router.post(
    "/triage/{triage_id}/transition", response_model=R[dict], summary="TriageCase 状态迁移"
)
def transition_triage_api(
    triage_id: str,
    body: TriageTransitionIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = noise_intelligence.transition_triage_case(
            db,
            triage_id=triage_id,
            project_id=current.project_id or 0,
            target=body.target,
        )
    except noise_intelligence.NoiseIntelligenceError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok({"id": row.id, "status": row.status})


# ── Benchmark (AUD-018) ─────────────────────────────────
class DatasetIn(BaseModel):
    dataset_key: str = Field(min_length=1, max_length=120)
    task_type: str = Field(default="learning", max_length=40)


class SampleIn(BaseModel):
    sample_id: str = Field(min_length=1, max_length=120)
    golden_labels: list[str] = Field(min_length=1)
    input_refs: list[str] = Field(default_factory=list)
    source: str = ""
    labeler: str = ""
    reviewer: str = ""


@router.post("/benchmarks/datasets", response_model=R[dict], summary="创建 Benchmark 数据集")
def create_dataset_api(
    body: DatasetIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        row = benchmark_service.create_dataset(
            db,
            project_id=current.project_id,
            dataset_key=body.dataset_key,
            task_type=body.task_type,
            created_by=getattr(current.user, "id", None),
        )
    except benchmark_service.BenchmarkError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok({"id": row.id, "dataset_key": row.dataset_key, "revision": row.revision})


@router.post(
    "/benchmarks/datasets/{dataset_id}/samples", response_model=R[dict], summary="追加 Benchmark 样本"
)
def add_sample_api(
    dataset_id: str,
    body: SampleIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        row = benchmark_service.add_sample(
            db,
            dataset_id,
            sample_id=body.sample_id,
            golden_labels=body.golden_labels,
            input_refs=body.input_refs,
            source=body.source,
            labeler=body.labeler,
            reviewer=body.reviewer,
        )
    except benchmark_service.BenchmarkError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok({"id": row.id, "sample_id": row.sample_id})


@router.post(
    "/benchmarks/datasets/{dataset_id}/freeze", response_model=R[dict], summary="冻结数据集"
)
def freeze_dataset_api(
    dataset_id: str,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = benchmark_service.freeze_dataset(
            db, dataset_id, approved_by=getattr(current.user, "id", None)
        )
    except benchmark_service.BenchmarkError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(
        {
            "id": row.id,
            "status": row.status,
            "sample_count": row.sample_count,
            "content_hash": row.content_hash,
            "gate_eligible": row.gate_eligible,
        }
    )


@router.get("/benchmarks/runs/{run_id}", response_model=R[dict], summary="Benchmark 结果")
def get_benchmark_run_api(
    run_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        run = benchmark_service.get_run(db, run_id)
    except benchmark_service.BenchmarkError as exc:
        raise _bad(str(exc), 404) from None
    return R.ok(
        {
            "id": run.id,
            "dataset_id": run.dataset_id,
            "agent_key": run.agent_key,
            "status": run.status,
            "result_status": run.result_status,
            "metrics": run.metrics_json,
            "per_sample": run.per_sample_json,
        }
    )


# ── Change Impact (AUD-017) ─────────────────────────────
class ImpactIn(BaseModel):
    base_sha: str = Field(min_length=7, max_length=40)
    head_sha: str = Field(min_length=7, max_length=40)
    failed_case_ids: list[str] = Field(default_factory=list)
    changed_contract_ids: list[str] = Field(default_factory=list)
    ai_proposed_case_ids: list[str] = Field(default_factory=list)


@router.post("/impact/plan", response_model=R[dict], summary="拉取真实 diff 并生成回归影响计划")
def impact_plan_api(
    body: ImpactIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    from pathlib import Path

    repo_path = str(Path(__file__).resolve().parents[4])
    try:
        plan = impact_service.build_impact_plan(
            db,
            project_id=current.project_id or 0,
            base_sha=body.base_sha,
            head_sha=body.head_sha,
            repo_path=repo_path,
            failed_case_ids=body.failed_case_ids,
            changed_contract_ids=body.changed_contract_ids,
            ai_proposed_case_ids=body.ai_proposed_case_ids or None,
        )
    except impact_service.ImpactError as exc:
        db.rollback()
        raise _bad(str(exc), 422) from None
    return R.ok(plan.payload())


# ── Platform binding / preflight (AUD-020) ──────────────
class PlatformBindingIn(BaseModel):
    target_type: str = Field(pattern="^(AC|CASE)$")
    target_id: str = Field(min_length=1, max_length=80)
    platform_id: str = Field(min_length=1, max_length=40)
    os_version: str = ""
    browser_or_app_version: str = ""
    device_model: str = ""
    driver_name: str = ""
    driver_version: str = ""
    node_id: str = ""
    test_profile: str = ""
    evidence_refs: list[str] = Field(default_factory=list)


class PlatformPreflightIn(BaseModel):
    platforms: list[str] = Field(min_length=1)


@router.post(
    "/platforms/bindings", response_model=R[dict], summary="创建平台绑定（状态服务端计算）"
)
def create_platform_binding_api(
    body: PlatformBindingIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        row = platform_binding_service.create_binding(
            db,
            project_id=current.project_id or 0,
            target_type=body.target_type,
            target_id=body.target_id,
            platform_id=body.platform_id,
            os_version=body.os_version,
            browser_or_app_version=body.browser_or_app_version,
            device_model=body.device_model,
            driver_name=body.driver_name,
            driver_version=body.driver_version,
            node_id=body.node_id,
            test_profile=body.test_profile,
            evidence_refs=body.evidence_refs,
        )
    except platform_binding_service.PlatformBindingError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(
        {
            "id": row.id,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "platform_id": row.platform_id,
            "capability_status": row.capability_status,
        }
    )


@router.get("/platforms/matrix", response_model=R[dict], summary="按平台聚合（不隐藏未验证）")
def platform_matrix_api(
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    return R.ok(platform_binding_service.platform_matrix(db, project_id=current.project_id or 0))


@router.post("/platforms/preflight", response_model=R[dict], summary="多端 Preflight")
def platform_preflight_api(
    body: PlatformPreflightIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    return R.ok(platform_binding_service.preflight_platform(db, body.platforms))


# ── Agent task plan (AUD-013) ───────────────────────────
class AgentTaskIn(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)
    include: list[str] | None = None


@router.post("/agent-tasks", response_model=R[dict], summary="A0 任务计划 Draft")
def create_agent_task_api(
    body: AgentTaskIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    from app.aiqe.agents.orchestrator import build_plan
    from app.aiqe.agents.protocol import AgentContext
    from app.aiqe.agents.registry import get_agent

    try:
        plan = build_plan(body.goal, include=tuple(body.include) if body.include else None)
    except Exception as exc:  # PlanError
        raise _bad(str(exc)) from None
    agent = get_agent("A0")
    result = agent.execute(AgentContext(project_id=current.project_id or 0), body.goal)
    return R.ok(
        {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "agent_key": task.agent_key,
                    "depends_on": list(task.depends_on),
                    "allowed_tools": list(task.allowed_tools),
                }
                for task in plan.order()
            ],
            "a0_status": result.status,
            "a0_output": result.output,
        }
    )


@router.post(
    "/regressions/{regression_id}/sync", response_model=R[dict], summary="回归终态同步（幂等）"
)
def sync_regression_api(
    regression_id: int,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
    _edit: CurrentUser = Depends(_edit),
):
    from app.aiqe.services.regression_service import RegressionNotFound, get_regression

    try:
        regression = get_regression(db, regression_id, current.project_id or 0)
    except RegressionNotFound:
        raise _bad(f"回归请求不存在: {regression_id}", 404) from None
    if not regression.verification_run_id:
        return R.ok({"regression_id": regression.id, "skipped": True, "reason": "NO_RUN"})
    result = regression_terminal.handle_run_terminal(
        db, run_id=regression.verification_run_id
    )
    db.commit()
    return R.ok(result.payload())


__all__ = ["router"]
