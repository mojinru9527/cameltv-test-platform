"""AI 产物审核服务 —— 列表/详情/采纳/驳回/导入正式资产。

治理核心（文档 §M0 验收）：导入守卫「未审核不得进正式库」——
只有 review_status == 'approved' 的产物才允许导入正式资产。
`import_artifact` 为统一导入分发入口，按 artifact_type 五类分发：
- test_case / api_case → 用例库 TestCase（case_type="api"）
- functional_case → 用例库 TestCase（case_type="manual"）
- ui_case → 用例库 TestCase（case_type="ui"，[UI] 标题前缀幂等）
- requirement → 需求库 RequirementDocument（file_type="md"）
- 其他类型 → APIException 拒绝
约定：写函数只 `db.flush()`，由调用方（路由）commit（用例/需求创建函数内部 commit）。
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


def batch_approve(
    db: Session,
    artifact_ids: list[int],
    project_id: int,
    reviewer_id: int,
    comment: str = "",
) -> dict:
    """批量采纳 AI 产物（去重、逐条复用 approve，事务由调用方统一 commit）。"""
    ids = list(dict.fromkeys(artifact_ids or []))
    approved: list[int] = []
    missing: list[int] = []
    for aid in ids:
        row = approve(db, aid, project_id, reviewer_id, comment)
        if row is not None:
            approved.append(aid)
        else:
            missing.append(aid)
    return {"approved": approved, "missing": missing}


def batch_reject(
    db: Session,
    artifact_ids: list[int],
    project_id: int,
    reviewer_id: int,
    comment: str = "",
) -> dict:
    """批量驳回 AI 产物（去重、逐条复用 reject，事务由调用方统一 commit）。"""
    ids = list(dict.fromkeys(artifact_ids or []))
    rejected: list[int] = []
    missing: list[int] = []
    for aid in ids:
        row = reject(db, aid, project_id, reviewer_id, comment)
        if row is not None:
            rejected.append(aid)
        else:
            missing.append(aid)
    return {"rejected": rejected, "missing": missing}


# artifact_type → (case_type, 默认 domain)：functional_case 默认「用户端」，
# api_case/test_case 默认「接口测试」（均可被 content.domain 覆盖）。
_CASE_TYPE_BY_ARTIFACT: dict[str, tuple[str, str]] = {
    "test_case": ("api", "接口测试"),
    "api_case": ("api", "接口测试"),
    "functional_case": ("manual", "用户端"),
}


def import_artifact(db: Session, artifact_id: int, project_id: int, operator_id: int = 0) -> dict:
    """统一导入分发入口：守卫通过后按 artifact_type 分发到用例库/需求库。

    治理守卫（沿用历史 import_to_test_case）：
    - 产物必须存在且属于当前项目，否则 404；
    - review_status == 'imported' → 拒绝重复导入；
    - review_status != 'approved' → 403（落实「未审核不得进正式库」）。
    分发：test_case/api_case→case_type="api"、functional_case→"manual"、ui_case→"ui"
    （均入 TestCase，ref_type="test_case"）；requirement→需求库 RequirementDocument
    （ref_type="requirement_document"）；其他类型 APIException 拒绝。
    返回 {"artifact_id", "ref_type", "ref_id"}；ref_type=="test_case" 时附带旧键 "case_id"。
    """
    row = get_artifact(db, artifact_id, project_id)
    if not row:
        raise APIException(code=404, msg="AI 产物不存在", http_status=404)
    if row.review_status == "imported":
        raise APIException(code=1, msg="该产物已导入，请勿重复导入")
    if row.review_status != "approved":
        raise forbidden("未审核通过的 AI 产物不允许导入正式用例库")

    try:
        payload = json.loads(row.content_json or "{}")
    except (json.JSONDecodeError, TypeError):
        raise APIException(code=1, msg="AI 产物内容解析失败")
    if not isinstance(payload, dict):
        raise APIException(code=1, msg="AI 产物内容解析失败")

    if row.artifact_type in _CASE_TYPE_BY_ARTIFACT:
        result = _import_case(db, row, payload, project_id)
    elif row.artifact_type == "ui_case":
        result = _import_ui_case(db, row, payload, project_id)
    elif row.artifact_type == "requirement":
        result = _import_requirement(db, row, payload, project_id, operator_id)
    else:
        raise APIException(code=1, msg=f"artifact_type={row.artifact_type} 暂不支持导入")

    if result["ref_type"] == "test_case":
        result["case_id"] = result["ref_id"]  # 旧键兼容
    return result


def import_to_test_case(db: Session, artifact_id: int, project_id: int) -> dict:
    """薄封装（向后兼容旧入口）：仅三类用例产物（test_case/api_case/functional_case）
    允许经此导入，其余类型拒绝；实际导入逻辑委托 `import_artifact` 分发。
    """
    row = get_artifact(db, artifact_id, project_id)
    if not row:
        raise APIException(code=404, msg="AI 产物不存在", http_status=404)
    if row.artifact_type not in _CASE_TYPE_BY_ARTIFACT:
        raise APIException(code=1, msg=f"artifact_type={row.artifact_type} 暂不支持导入用例库")
    return import_artifact(db, artifact_id, project_id)


def _import_case(db: Session, row: AiArtifact, payload: dict, project_id: int) -> dict:
    """三类用例产物（test_case/api_case/functional_case）导入正式用例库。"""
    from app.services import test_case_service

    case_type, default_domain = _CASE_TYPE_BY_ARTIFACT[row.artifact_type]

    data = {
        "project_id": project_id,
        "title": payload.get("title") or row.title,
        "domain": payload.get("domain") or default_domain,
        "module": payload.get("module", ""),
        "case_type": case_type,
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
    # 先标记 artifact 为已导入（占位 ref_id），再调用 create_case（内部 commit），
    # 最后回填实际 ref_id（flush），由调用方（路由）统一 commit。
    row.review_status = "imported"
    row.imported_ref_type = "test_case"
    row.imported_ref_id = 0  # 占位，create_case 成功后更新
    db.flush()

    case = test_case_service.create_case(db, data)  # commits internally

    row.imported_ref_id = case["id"]
    db.flush()
    return {"artifact_id": row.id, "ref_type": "test_case", "ref_id": case["id"]}


def _import_ui_case(db: Session, row: AiArtifact, payload: dict, project_id: int) -> dict:
    """ui_case 产物导入正式用例库（case_type="ui"，[UI] 标题前缀幂等）。"""
    from app.services import test_case_service

    title = (payload.get("title") or row.title).strip()
    if not title.startswith("[UI]"):
        title = f"[UI] {title}"[:220]
    data = {
        "project_id": project_id,
        "title": title,
        "domain": payload.get("domain") or "用户端",
        "module": payload.get("module", ""),
        "case_type": "ui",
        "priority": payload.get("priority", "P2"),
        "preconditions": payload.get("preconditions", ""),
        "steps": json.dumps(payload.get("steps", []), ensure_ascii=False),
        "expected_result": payload.get("expected_result", ""),
        "tags": json.dumps(payload.get("tags") or ["UI自动化", "auto:dsh"], ensure_ascii=False),
        "case_design_method": payload.get("case_design_method", "场景法"),
        "positive_negative": payload.get("positive_negative", ""),
        "test_data_note": payload.get("test_data_note", ""),
        "status": "draft",
        "source": "ai_generated",
    }
    # 同一占位模式：先置 artifact imported（flush）→ create_case（内部 commit）→ 回填 ref_id（flush）。
    row.review_status = "imported"
    row.imported_ref_type = "test_case"
    row.imported_ref_id = 0  # 占位，create_case 成功后更新
    db.flush()

    case = test_case_service.create_case(db, data)  # commits internally

    row.imported_ref_id = case["id"]
    db.flush()
    return {"artifact_id": row.id, "ref_type": "test_case", "ref_id": case["id"]}


def _import_requirement(db: Session, row: AiArtifact, payload: dict, project_id: int, operator_id: int) -> dict:
    """requirement 产物导入需求库（RequirementDocument，file_type="md"）。"""
    from app.services import requirement_service

    content = payload.get("content") or payload.get("markdown") or ""
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, indent=2)
    if not content.strip():
        content = json.dumps(payload, ensure_ascii=False, indent=2)  # 兜底：整 payload 留痕

    # 与用例导入同一占位模式：先置 artifact imported（flush）→ create_requirement
    # （内部 commit）→ 回填 imported_ref_id（flush）。
    row.review_status = "imported"
    row.imported_ref_type = "requirement_document"
    row.imported_ref_id = 0  # 占位，create_requirement 成功后更新
    db.flush()

    doc = requirement_service.create_requirement(
        db,
        project_id=project_id,
        creator_id=operator_id,
        title=(payload.get("title") or row.title).strip(),
        file_type="md",
        source_ref=f"dsh_artifact:{row.id}",
        source_url=payload.get("source_url") if isinstance(payload.get("source_url"), str) else "",
        content=content,
        commit=True,  # 与用例导入同风格（内部 commit）
    )

    row.imported_ref_id = doc["id"]
    db.flush()
    return {"artifact_id": row.id, "ref_type": "requirement_document", "ref_id": doc["id"]}


def import_artifacts_to_test_cases(db: Session, artifact_ids: list[int], project_id: int) -> list[dict]:
    """批量导入审核通过的 AI 产物 —— 批量导入的唯一受治理入口（M4 批量路由须经此）。

    治理门（文档 §M0）：一次导入多于 1 条时，需全局开关 `ai_artifact_allow_batch_import=True`
    才放行；否则拒绝（403），避免绕过逐条人审批量灌入正式库。
    每条改走 `import_artifact` 分发（可混入 ui_case/requirement，各归其库），
    仍复用其「未审核不得进正式库」守卫。
    """
    ids = list(dict.fromkeys(artifact_ids or []))
    if len(ids) > 1 and not settings.ai_artifact_allow_batch_import:
        raise forbidden("批量导入未开启（ai_artifact_allow_batch_import=False），请逐条导入")
    return [import_artifact(db, aid, project_id) for aid in ids]
