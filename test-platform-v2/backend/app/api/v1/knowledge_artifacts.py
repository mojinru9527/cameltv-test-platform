"""知识中心 API 路由 —— 产物/迭代（Batch 181 P2-10 拆分）。

从 knowledge.py 拆分：/ai-artifacts（列表/详情/批量与单条审核/导入）、
/skills、/iterations、/predict/regression-scope。

路由层不直连 ORM（Batch 181 强制）：查询与写入全部收敛至
artifact_service / skill_service / snapshot_service / regression_predictor；
commit 语义与拆分前一致（保留在路由层）。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.knowledge import (
    AiArtifactOut,
    ArtifactBatchImportRequest,
    ArtifactBatchReviewRequest,
    ArtifactImportRequest,
    ArtifactReviewRequest,
    CompareSnapshotsOut,
    KnowledgeIterationCreate,
    KnowledgeIterationOut,
    KnowledgeSnapshotOut,
    RegressionPredictionItem,
    RegressionPredictionOut,
    RegressionPredictionRequest,
)

from app.services import audit_service
from app.services.knowledge import artifact_service, snapshot_service
from app.services.knowledge.snapshot_service import compare_iterations, get_snapshots

logger = logging.getLogger("knowledge")
router = APIRouter(prefix="/knowledge", tags=["知识中心-产物/迭代"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = "") -> None:
    audit_service.write_audit(
        db,
        user_id=cu.user.id if cu.user else 0,
        username=(cu.user.nickname or cu.user.username) if cu.user else "",
        project_id=cu.project_id or 0,
        action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ═══════════════════════════════════════════════════════
# AI 产物审核台
# ═══════════════════════════════════════════════════════

@router.get("/ai-artifacts", response_model=R[Page[AiArtifactOut]], summary="AI 产物列表")
def list_artifacts(
    review_status: str | None = Query(None),
    artifact_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    rows, total = artifact_service.list_artifacts(
        db, current.project_id or 0,
        review_status=review_status, artifact_type=artifact_type,
        page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[AiArtifactOut.model_validate(r) for r in rows],
    ))


@router.get("/ai-artifacts/{artifact_id}", response_model=R[AiArtifactOut], summary="AI 产物详情")
def get_artifact(
    artifact_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    row = artifact_service.get_artifact(db, artifact_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="AI 产物不存在")
    return R.ok(AiArtifactOut.model_validate(row))


# ── 批量审核/导入（Batch 94；静态路径必须先于 {artifact_id} 注册，避免 422）──

@router.post("/ai-artifacts/batch-approve", response_model=R[dict], summary="批量采纳 AI 产物")
def batch_approve_artifacts(
    body: ArtifactBatchReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    result = artifact_service.batch_approve(
        db, body.ids, current.project_id or 0, current.user.id, body.comment,
    )
    _audit(req, current, db, "knowledge:approve", f"artifacts#{len(result['approved'])}", body.comment)
    db.commit()
    return R.ok(result)


@router.post("/ai-artifacts/batch-reject", response_model=R[dict], summary="批量驳回 AI 产物")
def batch_reject_artifacts(
    body: ArtifactBatchReviewRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    result = artifact_service.batch_reject(
        db, body.ids, current.project_id or 0, current.user.id, body.comment,
    )
    _audit(req, current, db, "knowledge:reject", f"artifacts#{len(result['rejected'])}", body.comment)
    db.commit()
    return R.ok(result)


@router.post("/ai-artifacts/batch-import", response_model=R[dict], summary="批量导入 AI 用例产物")
def batch_import_artifacts(
    body: ArtifactBatchImportRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("ai_artifact:import")),
    db: Session = Depends(get_db),
):
    """批量导入审核通过的 AI 用例产物（受 ai_artifact_allow_batch_import 治理开关约束）。"""
    result = artifact_service.import_artifacts_to_test_cases(
        db, body.ids, current.project_id or 0,
    )
    _audit(req, current, db, "ai_artifact:import", f"artifacts#{len(result)}", "")
    db.commit()
    return R.ok({"imported": result})


@router.post("/ai-artifacts/{artifact_id}/approve", response_model=R[AiArtifactOut], summary="采纳 AI 产物")
def approve_artifact(
    artifact_id: int,
    req: Request,
    body: ArtifactReviewRequest,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    row = artifact_service.approve(db, artifact_id, current.project_id or 0, current.user.id, body.comment)
    if not row:
        return R(code=404, msg="AI 产物不存在")
    _audit(req, current, db, "knowledge:approve", f"artifact#{artifact_id}", body.comment)
    db.commit()
    db.refresh(row)
    return R.ok(AiArtifactOut.model_validate(row))


@router.post("/ai-artifacts/{artifact_id}/reject", response_model=R[AiArtifactOut], summary="驳回 AI 产物")
def reject_artifact(
    artifact_id: int,
    req: Request,
    body: ArtifactReviewRequest,
    current: CurrentUser = Depends(require_permission("knowledge:approve")),
    db: Session = Depends(get_db),
):
    row = artifact_service.reject(db, artifact_id, current.project_id or 0, current.user.id, body.comment)
    if not row:
        return R(code=404, msg="AI 产物不存在")
    _audit(req, current, db, "knowledge:reject", f"artifact#{artifact_id}", body.comment)
    db.commit()
    db.refresh(row)
    return R.ok(AiArtifactOut.model_validate(row))


@router.post("/ai-artifacts/{artifact_id}/import-to-test-cases", response_model=R[dict], summary="导入正式用例库")
def import_artifact(
    artifact_id: int,
    req: Request,
    body: ArtifactImportRequest,
    current: CurrentUser = Depends(require_permission("ai_artifact:import")),
    db: Session = Depends(get_db),
):
    """治理守卫：仅 review_status='approved' 的 AI 用例产物允许导入正式库。"""
    result = artifact_service.import_to_test_case(db, artifact_id, current.project_id or 0)
    _audit(req, current, db, "ai_artifact:import", f"artifact#{artifact_id} → case#{result['case_id']}", body.comment)
    db.commit()
    return R.ok(result)


# ═══════════════════════════════════════════════════════
# Skills 模板（Layer 9）
# ═══════════════════════════════════════════════════════

class SkillApplyRequest(BaseModel):
    params: dict | None = None


class SkillApplyResult(BaseModel):
    success: bool
    skill: str = ""
    result: str = ""
    agent_run_id: int | None = None
    knowledge_context: str = ""
    prompt: str = ""
    params: dict | None = None
    note: str = ""
    error: str = ""


@router.get("/skills", response_model=R[list[dict]], summary="列出可用 Skills 模板")
def list_skills(
    current: CurrentUser = Depends(require_permission("knowledge:view")),
):
    """列出所有预置 AI 能力模板（生成用例、分析缺陷、提取契约等）。"""
    from app.services.knowledge.skill_service import list_skills
    return R.ok(list_skills())


@router.post("/skills/{skill_name}/apply", response_model=R[SkillApplyResult], summary="应用 Skills 模板")
async def apply_skill(
    skill_name: str,
    body: SkillApplyRequest,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """应用指定的 AI 能力模板到当前项目知识库，返回 AI 处理结果。"""
    from app.services.knowledge.skill_service import apply_skill_in_new_session
    result = await apply_skill_in_new_session(
        current.project_id or 0,
        skill_name,
        body.params,
    )
    _audit(req, current, db, "knowledge:skill_apply", skill_name, str(result.get("success", False)))
    db.commit()
    return R.ok(SkillApplyResult(**result))


# ═══════════════════════════════════════════════════════
# M6 迭代知识包
# ═══════════════════════════════════════════════════════

@router.post("/iterations", response_model=R[KnowledgeIterationOut], summary="创建迭代")
def create_iteration(
    body: KnowledgeIterationCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    it = snapshot_service.create_iteration(
        db,
        current.project_id or 0,
        iteration_name=body.iteration_name,
        version=body.version,
        start_date=body.start_date,
        end_date=body.end_date,
        description=body.description,
    )
    _audit(req, current, db, "knowledge:iteration_create", f"iteration#{it.id}", body.iteration_name)
    db.commit()
    db.refresh(it)
    return R.ok(KnowledgeIterationOut.model_validate(it))


@router.get("/iterations", response_model=R[Page[KnowledgeIterationOut]], summary="迭代列表")
def list_iterations(
    status: str | None = Query(None, description="active/closed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    rows, total = snapshot_service.list_iterations(
        db, current.project_id or 0,
        status=status, page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[KnowledgeIterationOut.model_validate(r) for r in rows],
    ))


@router.get("/iterations/{iteration_id}", response_model=R[KnowledgeIterationOut], summary="迭代详情")
def get_iteration(
    iteration_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    it = snapshot_service.get_iteration(db, iteration_id, current.project_id or 0)
    if not it:
        return R(code=404, msg="迭代不存在")
    return R.ok(KnowledgeIterationOut.model_validate(it))


@router.post("/iterations/{iteration_id}/close", response_model=R[dict], summary="关闭迭代并生成快照")
def close_iteration(
    iteration_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("knowledge:manage")),
    db: Session = Depends(get_db),
):
    """关闭迭代，自动创建 entity/relation/chunk/stats 四种快照。"""
    from app.services.knowledge.snapshot_service import close_iteration_in_new_session
    result = close_iteration_in_new_session(iteration_id, current.project_id or 0)
    _audit(req, current, db, "knowledge:iteration_close", f"iteration#{iteration_id}", str(result))
    db.commit()
    if result.get("success"):
        return R.ok(result)
    return R(code=400, msg=result.get("error", "关闭失败"))


@router.get("/iterations/{iteration_id}/snapshots", response_model=R[list[KnowledgeSnapshotOut]], summary="迭代快照列表")
def list_snapshots(
    iteration_id: int,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """获取某个迭代的所有快照（entity/relation/chunk/stats）。"""
    snaps = get_snapshots(db, iteration_id)
    return R.ok([KnowledgeSnapshotOut.model_validate(s) for s in snaps])


@router.get("/iterations/{iteration_id}/compare", response_model=R[CompareSnapshotsOut], summary="跨迭代对比")
def compare_iteration(
    iteration_id: int,
    base_iteration_id: int = Query(..., description="基准迭代 ID"),
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """对比两个迭代的快照数据，返回增量和趋势。"""
    result = compare_iterations(db, base_iteration_id, iteration_id, current.project_id or 0)
    if not result:
        return R(code=404, msg="迭代不存在")
    return R.ok(CompareSnapshotsOut(**result))


# ═══════════════════════════════════════════════════════
# M6 回归范围预测
# ═══════════════════════════════════════════════════════

@router.post("/predict/regression-scope", response_model=R[RegressionPredictionOut], summary="回归范围预测")
def predict_regression_scope(
    body: RegressionPredictionRequest,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
):
    """输入变更的 API paths / modules，输出按风险排序的回归范围预测。"""
    from app.services.knowledge.regression_predictor import predict_regression_scope
    result = predict_regression_scope(
        current.project_id or 0,
        changed_paths=body.changed_paths,
        changed_modules=body.changed_modules,
    )
    return R.ok(RegressionPredictionOut(
        items=[RegressionPredictionItem(**i) for i in result["items"]],
        total_analyzed=result["total_analyzed"],
        high_risk_count=result["high_risk_count"],
    ))
