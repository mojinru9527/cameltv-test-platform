"""AI 产物审核服务 —— 列表/详情/采纳/驳回/导入正式资产。

治理核心（文档 §M0 验收）：`import_to_test_case` 守卫「未审核不得进正式用例库」——
只有 review_status == 'approved' 的产物才允许导入 TestCase。
约定：写函数只 `db.flush()`，由调用方（路由）commit。
"""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import APIException, forbidden
from app.models.knowledge import AiArtifact


def list_artifacts(
    db: Session,
    project_id: int,
    *,
    review_status: str | None = None,
    artifact_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AiArtifact], int]:
    stmt = select(AiArtifact).where(AiArtifact.project_id == project_id)
    cnt = select(func.count(AiArtifact.id)).where(AiArtifact.project_id == project_id)
    if review_status:
        stmt = stmt.where(AiArtifact.review_status == review_status)
        cnt = cnt.where(AiArtifact.review_status == review_status)
    if artifact_type:
        stmt = stmt.where(AiArtifact.artifact_type == artifact_type)
        cnt = cnt.where(AiArtifact.artifact_type == artifact_type)

    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(AiArtifact.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_artifact(db: Session, artifact_id: int, project_id: int) -> AiArtifact | None:
    row = db.get(AiArtifact, artifact_id)
    if not row or row.project_id != project_id:
        return None
    return row


def approve(db: Session, artifact_id: int, project_id: int, reviewer_id: int, comment: str = "") -> AiArtifact | None:
    row = get_artifact(db, artifact_id, project_id)
    if not row:
        return None
    row.review_status = "approved"
    row.reviewer_id = reviewer_id
    row.review_comment = comment
    db.flush()
    return row


def reject(db: Session, artifact_id: int, project_id: int, reviewer_id: int, comment: str = "") -> AiArtifact | None:
    row = get_artifact(db, artifact_id, project_id)
    if not row:
        return None
    row.review_status = "rejected"
    row.reviewer_id = reviewer_id
    row.review_comment = comment
    db.flush()
    return row


def import_to_test_case(db: Session, artifact_id: int, project_id: int) -> dict:
    """将审核通过的 AI 用例产物导入正式用例库。

    治理守卫：
    - 产物必须存在且属于当前项目；
    - review_status 必须为 'approved'，否则拒绝（403）——落实「未审核不得进正式库」；
    - artifact_type 必须为 'test_case'。
    """
    from app.services import test_case_service

    row = get_artifact(db, artifact_id, project_id)
    if not row:
        raise APIException(code=404, msg="AI 产物不存在", http_status=404)
    if row.review_status == "imported":
        raise APIException(code=1, msg="该产物已导入，请勿重复导入")
    if row.review_status != "approved":
        raise forbidden("未审核通过的 AI 产物不允许导入正式用例库")
    if row.artifact_type != "test_case":
        raise APIException(code=1, msg=f"artifact_type={row.artifact_type} 暂不支持导入用例库")

    try:
        payload = json.loads(row.content_json or "{}")
    except (json.JSONDecodeError, TypeError):
        raise APIException(code=1, msg="AI 产物内容解析失败")

    data = {
        "project_id": project_id,
        "title": payload.get("title") or row.title,
        "domain": payload.get("domain", "接口测试"),
        "module": payload.get("module", ""),
        "case_type": "api",
        "priority": payload.get("priority", "P2"),
        "preconditions": payload.get("preconditions", ""),
        "steps": json.dumps(payload.get("steps", []), ensure_ascii=False),
        "expected_result": payload.get("expected_result", ""),
        "api_method": payload.get("api_method", "GET"),
        "api_endpoint": payload.get("api_endpoint", ""),
        "api_headers": json.dumps(payload.get("api_headers", {}), ensure_ascii=False),
        "api_body": payload.get("api_body", ""),
        "api_assertions": json.dumps(payload.get("api_assertions", []), ensure_ascii=False),
        "status": "draft",
        "source": "ai_generated",
    }
    case = test_case_service.create_case(db, data)  # commits internally

    row.review_status = "imported"
    row.imported_ref_type = "test_case"
    row.imported_ref_id = case["id"]
    db.flush()
    return {"artifact_id": row.id, "case_id": case["id"]}


def import_artifacts_to_test_cases(db: Session, artifact_ids: list[int], project_id: int) -> list[dict]:
    """批量导入审核通过的 AI 用例产物 —— 批量导入的唯一受治理入口（M4 批量路由须经此）。

    治理门（文档 §M0）：一次导入多于 1 条时，需全局开关 `ai_artifact_allow_batch_import=True`
    才放行；否则拒绝（403），避免绕过逐条人审批量灌入正式用例库。
    每条仍复用单条 `import_to_test_case` 的「未审核不得进正式库」守卫。
    """
    ids = list(dict.fromkeys(artifact_ids or []))
    if len(ids) > 1 and not settings.ai_artifact_allow_batch_import:
        raise forbidden("批量导入未开启（ai_artifact_allow_batch_import=False），请逐条导入")
    return [import_to_test_case(db, aid, project_id) for aid in ids]
