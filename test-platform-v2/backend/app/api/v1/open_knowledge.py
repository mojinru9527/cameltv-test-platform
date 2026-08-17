"""开放 API 知识/计划查询面 — /api/v1/open/*（DSH 测试 Agent 框架，阶段 1/2）。

knowledge-mcp 经本组端点访问知识中心与测试计划（API Token 鉴权 + project 隔离）。
与 open_api.py（CI 触发/回写）分开成独立路由文件，遵守「路由文件 ≤20KB」守卫。

路由层禁 ORM（Batch 181 强制）：全部收敛至既有 service。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import APIException
from app.schemas.common import R

from app.api.v1.open_api import verify_api_token

if TYPE_CHECKING:
    from app.models.api_token import ApiToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/open", tags=["开放API-Agent查询面"])


# ── 知识源列表 ──

@router.get("/knowledge/sources", response_model=R[dict], summary="知识源列表（Agent 查询面）")
def open_list_knowledge_sources(
    source_type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """知识中心知识源列表（需求/接口/用例/缺陷/执行结果），Agent onboarding 用。"""
    from app.services.knowledge.source_service import list_sources

    rows, total = list_sources(
        db, token.project_id,
        source_type=source_type, keyword=keyword, page=page, page_size=page_size,
    )
    items = [{
        "id": r.id, "source_type": r.source_type, "source_id": r.source_id,
        "title": r.title, "version": r.version, "status": r.status,
        "freshness_score": getattr(r, "freshness_score", None),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


# ── 混合检索 ──

@router.post("/knowledge/search", response_model=R[list], summary="知识混合检索（Agent 查询面）")
def open_search_knowledge(
    body: dict,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """RAG 混合检索（rag 不可用时自动降级关键词），Agent 熟悉项目/定位用例用。"""
    from app.services.knowledge import search_service

    query = (body.get("query") or "").strip()
    if not query:
        raise APIException(code=400, msg="缺少 query")
    top_k = max(1, min(int(body.get("top_k", 8)), 50))
    mode = body.get("mode", "hybrid")
    chunk_type = body.get("chunk_type") or None

    # 与 knowledge_core 同逻辑：RAG 未启用/模型不可用 → 强制关键词
    if not settings.rag_enabled:
        mode = "keyword"
    else:
        from app.services.knowledge.embedding_service import embedding_service

        if not embedding_service.available():
            mode = "keyword"

    hits = search_service.hybrid_search(
        db, project_id=token.project_id, query=query, top_k=top_k,
        chunk_type=chunk_type, mode=mode,
    )
    return R.ok([{
        "chunk_id": h.chunk_id, "chunk_type": h.chunk_type, "title": h.title,
        "snippet": h.snippet, "score": h.score, "source_id": h.source_id,
        "source_name": h.source_name,
    } for h in hits])


# ── 模块拓扑（L0 骨架）──

@router.get("/knowledge/modules", response_model=R[dict], summary="模块拓扑（Agent 查询面）")
def open_get_module_topology(
    module: str | None = None,
    limit: int = 50,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """项目知识拓扑：模块实体 + 挂接的子实体（需求/用例/接口/设计稿）。

    L0 骨架的对外视图——Agent onboarding 先取拓扑定位影响面，再按需拉详情。
    """
    from app.services.knowledge.entity_service import get_module_topology

    return R.ok(get_module_topology(db, token.project_id, module=module, limit=limit))


# ── 需求列表 ──

@router.get("/requirements", response_model=R[dict], summary="需求文档列表（Agent 查询面）")
def open_list_requirements(
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """需求文档列表（不含全文），Agent 定位需求用。"""
    from app.services import requirement_service

    total, rows = requirement_service.list_requirements_page(
        db, token.project_id, keyword=keyword, page=page, page_size=page_size,
    )
    items = [{
        "id": row.id, "title": row.title, "version": row.version,
        "source_ref": row.source_ref or "", "file_type": row.file_type or "",
        "status": row.status or "", "extraction_status": row.extraction_status or "",
        "imported_func_count": row.imported_func_count or 0,
        "imported_api_count": row.imported_api_count or 0,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row, _creator in rows]
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


# ── 用例列表/回写 ──

@router.get("/test-cases", response_model=R[dict], summary="用例列表（Agent 查询面）")
def open_list_test_cases(
    module: str = "",
    domain: str = "",
    case_type: str = "",
    priority: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """用例列表（含三关联元数据：模块/需求追溯/接口契约），Agent 按图索骥用。"""
    from app.services import test_case_service

    items, total = test_case_service.list_cases(
        db, project_id=token.project_id, module=module, domain=domain,
        case_type=case_type, priority=priority, keyword=keyword,
        page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.post("/test-cases", response_model=R[dict], summary="用例直接入库（Agent 回写面）")
def open_create_test_case(
    body: dict,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """Agent 设计用例直接写入用例库（走 skill 规则产出，不经 AI 审核台）。

    2026-08-17 评审决策：用例生成规则单一事实源 = test-case-design skill，
    reviewer 审查留痕兜底。project 由 token 隔离，调用方不可指定。
    """
    from app.schemas.test_case import TestCaseCreate
    from app.services import test_case_service

    try:
        data = TestCaseCreate(**{**body, "project_id": token.project_id}).model_dump()
    except Exception as exc:  # noqa: BLE001 - pydantic 校验错误转 400
        raise APIException(code=400, msg=f"用例字段校验失败: {exc}")

    row = test_case_service.create_case(db, data)
    db.commit()
    token.last_used_at = datetime.now(timezone.utc)
    db.commit()

    # API 类型用例异步入知识中心（与 test_case_crud 同语义）
    if row.get("case_type") == "api":
        try:
            from app.services.knowledge import ingest_service

            ingest_service.ingest_test_case_in_new_session(token.project_id, row["id"])
        except Exception:
            logger.exception("Agent 回写用例入库知识中心失败: case_id=%s", row.get("id"))

    return R.ok({"id": row["id"], "case_id": row.get("case_id", ""), "title": row.get("title", "")})


# ── 测试计划查询面（阶段 2 api-tester 编排入口）──

@router.get("/plans", response_model=R[dict], summary="测试计划列表（Agent 查询面）")
def open_list_plans(
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """测试计划列表（含用例统计），api-tester 选择触发目标用。"""
    from app.services import test_plan_service

    items, total = test_plan_service.list_plans(
        db, project_id=token.project_id, status=status, keyword=keyword,
        page=page, page_size=page_size,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.get("/plans/{plan_id}", response_model=R[dict], summary="测试计划详情（Agent 查询面）")
def open_get_plan(
    plan_id: int,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """测试计划详情（含用例清单），api-tester 执行前核对用例/环境用。"""
    from app.services import test_plan_service

    row = test_plan_service.get_plan(db, plan_id, project_id=token.project_id)
    if not row:
        raise APIException(code=404, msg="计划不存在")
    return R.ok(row)


@router.get("/plans/{plan_id}/executions", response_model=R[dict], summary="计划执行记录（Agent 查询面）")
def open_list_plan_executions(
    plan_id: int,
    page: int = 1,
    page_size: int = 50,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """计划最近执行记录（含每条用例的 last_status），api-tester 判定/回读用。"""
    from app.services import test_plan_service

    items, total = test_plan_service.get_executions(
        db, plan_id, page=page, page_size=page_size, project_id=token.project_id,
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})
