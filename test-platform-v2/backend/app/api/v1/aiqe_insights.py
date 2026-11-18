"""AUD-014/015/017/018/019/020/013：v1.5 §06 目标契约的 REST 面。

所有路由都复用已交付的 service（不新增业务逻辑），并遵守统一的：
project scope（`current.project_id`）、RBAC（`menu:aiqe_runs` / `defect:update`）、
错误映射（400/403/404/422）、以及"前端不得自报事实"的约束。
"""
from __future__ import annotations


from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services import (
    benchmark_service,
    impact_service,
    platform_binding_service,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe", tags=["AIQE Capabilities"])

_console = require_permission("menu:aiqe_runs")
_edit = require_permission("defect:update")


def _bad(message: str, status: int = 400) -> APIException:
    return APIException(code=status, msg=message, http_status=status)


# ── Benchmark (AUD-018) ─────────────────────────────────
class DatasetIn(BaseModel):
    dataset_key: str = Field(min_length=1, max_length=120)
    task_type: str = Field(default="learning", max_length=40)


class BenchmarkRunIn(BaseModel):
    agent_key: str = Field(default="A6", max_length=16)
    agent_version: str = Field(default="", max_length=40)


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


@router.post(
    "/benchmarks/datasets/{dataset_id}/runs",
    response_model=R[dict],
    summary="运行 LLM Benchmark（服务端计算指标）",
)
def run_benchmark_api(
    dataset_id: str,
    body: BenchmarkRunIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        run = benchmark_service.run_llm_benchmark(
            db,
            dataset_id=dataset_id,
            project_id=current.project_id or 0,
            agent_key=body.agent_key,
            agent_version=body.agent_version,
        )
    except benchmark_service.BenchmarkError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(
        {
            "id": run.id,
            "dataset_id": run.dataset_id,
            "agent_key": run.agent_key,
            "status": run.status,
            "result_status": run.result_status,
            "metrics": run.metrics_json,
            "per_sample": run.per_sample_json,
            "token_usage": run.token_usage_json,
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


