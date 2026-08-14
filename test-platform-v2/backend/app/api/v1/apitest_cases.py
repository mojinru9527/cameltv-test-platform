"""接口测试 API 路由（用例生成域） —— /api/v1/apitest/*

Batch 181（FIX-173-P2-10）路由拆分：cases/generate、cases/batch-generate。
端点函数体与原 apitest.py 逐字一致；ApiEndpoint/TestCase ORM 查询收敛到
app.services.openapi_import_service / api_case_generation_service。
"""

from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.api_asset import BatchGenerateRequest, GenerateApiCasesRequest
from app.schemas.common import R
from app.services import openapi_import_service
from app.services.api_case_generation_service import (
    create_test_case_from_generated,
    generate_cases_from_endpoint,
)
from app.services.knowledge import ingest_service

router = APIRouter(prefix="/apitest", tags=["接口测试-用例生成"])


def _current_project_id(current: CurrentUser) -> int:
    """Derive current project from JWT token. Rejects missing project context."""
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


def _safe_json(raw: str, default=None):
    if not raw or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# ═══════════════════════════════════════════════════════
# 用例生成
# ═══════════════════════════════════════════════════════


@router.post("/cases/generate", response_model=R[dict], summary="单接口生成用例")
def generate_cases(
    body: GenerateApiCasesRequest,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("apitest:generate")),
    db: Session = Depends(get_db),
):
    """基于接口定义生成测试用例。"""
    pid = _current_project_id(current)

    # 获取 endpoint 数据
    if body.endpoint_id:
        ep = openapi_import_service.get_project_endpoint(db, body.endpoint_id, pid)
        if not ep:
            raise HTTPException(404, "接口资产不存在")
        endpoint_data = {
            "service_name": body.service_name,
            "module": body.module or ep.module,
            "method": ep.method,
            "path": ep.path,
            "summary": ep.summary,
            "request_schema": _safe_json(ep.request_schema, {}),
        }
    elif body.endpoint_data:
        endpoint_data = body.endpoint_data
    else:
        raise HTTPException(400, "请提供 endpoint_id 或 endpoint_data")

    cases = generate_cases_from_endpoint(endpoint_data, templates=body.templates)

    imported_ids = []
    if body.import_to_case_library:
        for c in cases:
            tc = create_test_case_from_generated(db, pid, c, body.endpoint_id)
            imported_ids.append(tc.id)
        db.commit()
        # M1 入库 hook：生成用例 → 沉淀为知识切片
        if imported_ids:
            background_tasks.add_task(
                ingest_service.ingest_test_cases_in_new_session,
                pid,
                imported_ids.copy(),
            )

    return R.ok(
        {
            "cases": cases,
            "total": len(cases),
            "imported_case_ids": imported_ids,
        }
    )


@router.post("/cases/batch-generate", response_model=R[dict], summary="批量生成用例")
def batch_generate_cases(
    body: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("apitest:generate")),
    db: Session = Depends(get_db),
):
    """批量多个接口生成测试用例。"""
    pid = _current_project_id(current)
    total_generated = 0
    all_imported_ids = []
    errors = []

    for ep_id in body.endpoint_ids:
        ep = openapi_import_service.get_project_endpoint(db, ep_id, pid)
        if not ep:
            errors.append({"endpoint_id": ep_id, "error": "接口资产不存在"})
            continue
        endpoint_data = {
            "service_name": "",
            "module": ep.module,
            "method": ep.method,
            "path": ep.path,
            "summary": ep.summary,
            "request_schema": _safe_json(ep.request_schema, {}),
        }
        cases = generate_cases_from_endpoint(endpoint_data, templates=body.templates)
        total_generated += len(cases)

        if body.import_to_case_library:
            for c in cases:
                tc = create_test_case_from_generated(db, pid, c, ep_id)
                all_imported_ids.append(tc.id)

    db.commit()
    # M1 入库 hook：批量生成用例 → 沉淀为知识切片
    if all_imported_ids:
        background_tasks.add_task(
            ingest_service.ingest_test_cases_in_new_session,
            pid,
            all_imported_ids.copy(),
        )

    return R.ok(
        {
            "total_generated": total_generated,
            "imported_case_ids": all_imported_ids,
            "errors": errors,
        }
    )


# ═══════════════════════════════════════════════════════
# 接口变更影响分析（C-API-AUTO-002）
# ═══════════════════════════════════════════════════════


class OpenApiChangeAnalyzeRequest(BaseModel):
    """新旧 OpenAPI spec 对比请求。"""

    old_spec: dict = Field(..., description="旧版本 OpenAPI/Swagger 文档（dict）")
    new_spec: dict = Field(..., description="新版本 OpenAPI/Swagger 文档（dict）")
    case_module: str | None = Field(None, description="仅分析指定模块的用例（可选）")
    as_markdown: bool = Field(
        False, description="返回 Markdown 报告（默认返回结构化 JSON）"
    )


@router.post("/cases/change-impact", response_model=R[dict], summary="接口变更影响分析")
def analyze_change_impact(
    body: OpenApiChangeAnalyzeRequest,
    current: CurrentUser = Depends(require_permission("apitest:generate")),
    db: Session = Depends(get_db),
):
    """对比新旧 OpenAPI 文档，输出变更接口清单与受影响用例。

    用途：版本迭代后接口变更的增量维护 —— 找出新增/删除/修改的接口，
    定位用例库中受影响的 API 用例，输出定向修改建议（无需全量重生成）。
    """
    pid = _current_project_id(current)
    from app.services.api_change_impact_service import (
        analyze_openapi_change,
        changes_to_markdown,
    )

    result = analyze_openapi_change(
        db,
        pid,
        body.old_spec,
        body.new_spec,
        case_module=body.case_module,
    )
    if body.as_markdown:
        return R.ok({"markdown": changes_to_markdown(result)})
    return R.ok(result)
