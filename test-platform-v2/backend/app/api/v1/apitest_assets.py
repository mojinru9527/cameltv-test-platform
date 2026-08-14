"""接口测试 API 路由（资产域） —— /api/v1/apitest/*

Batch 181（FIX-173-P2-10）路由拆分：服务 / 接口资产 CRUD + OpenAPI 导入。
端点函数体与原 apitest.py 逐字一致；ApiService/ApiEndpoint/TestCase/TestPlan ORM
查询收敛到 app.services.openapi_import_service / api_case_generation_service /
test_plan_service。
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.api_asset import (
    ApiEndpointCreate,
    ApiEndpointOut,
    ApiEndpointUpdate,
    ApiServiceCreate,
    ApiServiceOut,
    ApiServiceUpdate,
    OpenApiImportConfirmRequest,
    OpenApiImportPreviewRequest,
)
from app.schemas.common import R
from app.services import openapi_import_service
from app.services.api_case_generation_service import (
    create_test_case_from_generated,
    generate_cases_from_endpoint,
)
from app.services.knowledge import ingest_service
from app.services.test_plan_service import create_plan_with_cases

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apitest", tags=["接口测试-资产"])


# ═══════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════

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


def _resolve_spec(source_type: str, source_ref: str, spec_content: str | None) -> dict | None:
    """从不同来源解析 OpenAPI spec 为 dict。

    支持:
    - openapi_url: 直接 URL (JSON/YAML)
    - swagger_doc_url: Knife4j/Swagger UI doc.html — 自动发现底层 spec URL
    - openapi_text/file: 文字/文件内容
    """
    import yaml as _yaml

    raw = spec_content or ""

    # URL 导入
    if source_type in ("openapi_url", "swagger_doc_url") and source_ref:
        try:
            import httpx
            from urllib.parse import urljoin, urlparse

            resp = httpx.get(source_ref, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            raw = resp.text

            # 如果返回的是 HTML 页面（Knife4j/Swagger UI），尝试发现真实 spec URL
            if raw.strip().lower().startswith("<!doctype") or "<html" in raw[:512].lower():
                parsed = urlparse(source_ref)
                base = f"{parsed.scheme}://{parsed.netloc}"

                # 候选 spec URL 列表（按优先级）
                candidates = [
                    f"{base}/v3/api-docs",
                    f"{base}/v2/api-docs",
                    f"{base}/swagger-resources",
                ]

                # doc.html → 检查同级路径下的 v3/api-docs
                if parsed.path.endswith("doc.html"):
                    group_base = parsed.path.rsplit("/", 1)[0]
                    candidates.insert(0, f"{base}{group_base}/v3/api-docs")
                    candidates.insert(1, f"{base}{group_base}/v2/api-docs")

                # 尝试各候选 URL
                spec_raw = None
                for url in candidates:
                    try:
                        r = httpx.get(url, timeout=15)
                        if r.status_code == 200:
                            body = r.text.strip()
                            # swagger-resources 返回 JSON 数组 — 取第一个 location
                            if url.endswith("swagger-resources"):
                                try:
                                    resources = json.loads(body)
                                    if isinstance(resources, list) and resources:
                                        loc = resources[0].get("location") or resources[0].get("url", "")
                                        if loc:
                                            loc_url = urljoin(base, loc)
                                            r2 = httpx.get(loc_url, timeout=15)
                                            if r2.status_code == 200:
                                                spec_raw = r2.text
                                                break
                                    continue
                                except Exception:
                                    logger.warning("接口发现响应解析失败，跳过该 endpoint")
                            spec_raw = body
                            break
                    except Exception:
                        continue

                if spec_raw:
                    raw = spec_raw
                else:
                    return None
        except Exception:
            return None

    # 文件/文本导入 — raw 已在 spec_content 中
    if not raw:
        return None

    # 解析 JSON/YAML
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        try:
            return _yaml.safe_load(raw)
        except Exception:
            return None


def _batch_generate_for_endpoints(db: Session, batch_id: int, project_id: int) -> tuple[int, list[int]]:
    """导入后批量生成基础用例。返回 (生成条数, 创建的用例 id 列表)。"""
    endpoints = openapi_import_service.list_endpoints_by_import_batch(db, batch_id, project_id)
    count = 0
    case_ids: list[int] = []
    for ep in endpoints:
        ep_data = {
            "service_name": "",
            "module": ep.module,
            "method": ep.method,
            "path": ep.path,
            "summary": ep.summary,
            "request_schema": _safe_json(ep.request_schema, {}),
        }
        cases = generate_cases_from_endpoint(ep_data, templates=["basic"])
        for c in cases:
            tc = create_test_case_from_generated(db, project_id, c, ep.id)
            case_ids.append(tc.id)
            count += 1
    db.commit()
    return count, case_ids


# ═══════════════════════════════════════════════════════
# 服务管理
# ═══════════════════════════════════════════════════════

@router.get("/services", response_model=R[list[ApiServiceOut]], summary="服务列表")
def list_services(
    current: CurrentUser = Depends(require_permission("apitest:view")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    rows = openapi_import_service.list_project_services(db, pid)
    return R.ok([ApiServiceOut.model_validate(r) for r in rows])


@router.post("/services", response_model=R[ApiServiceOut], summary="创建服务")
def create_service(
    body: ApiServiceCreate,
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    svc = openapi_import_service.create_api_service(db, project_id=pid, **body.model_dump())
    db.commit()
    db.refresh(svc)
    return R.ok(ApiServiceOut.model_validate(svc))


@router.put("/services/{service_id}", response_model=R[ApiServiceOut], summary="更新服务")
def update_service(
    service_id: int,
    body: ApiServiceUpdate,
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    svc = openapi_import_service.get_project_service(db, service_id, pid)
    if not svc:
        raise HTTPException(404, "服务不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(svc, k, v)
    db.commit()
    db.refresh(svc)
    return R.ok(ApiServiceOut.model_validate(svc))


@router.delete("/services/{service_id}", response_model=R[dict], summary="删除服务")
def delete_service(
    service_id: int,
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    """Delete an unreferenced service in the active project."""
    pid = _current_project_id(current)
    svc = openapi_import_service.get_project_service(db, service_id, pid)
    if not svc:
        raise HTTPException(404, "服务不存在")

    if openapi_import_service.service_has_endpoints(db, service_id):
        raise HTTPException(409, "服务仍被接口资产引用，无法删除")

    db.delete(svc)
    db.commit()
    return R.ok({"id": service_id})


# ═══════════════════════════════════════════════════════
# 接口资产管理
# ═══════════════════════════════════════════════════════

@router.get("/endpoints", response_model=R[dict], summary="接口资产列表（分页）")
def list_endpoints(
    service_id: int | None = Query(None),
    module: str | None = Query(None),
    method: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("apitest:view")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    rows, total = openapi_import_service.list_project_endpoints(
        db, pid,
        service_id=service_id, module=module, method=method,
        keyword=keyword, page=page, page_size=page_size,
    )
    return R.ok({
        "total": total, "page": page, "page_size": page_size,
        "items": [ApiEndpointOut.model_validate(r) for r in rows],
    })


@router.post("/endpoints", response_model=R[ApiEndpointOut], summary="手动创建接口资产")
def create_endpoint(
    body: ApiEndpointCreate,
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    if not openapi_import_service.get_project_service(db, body.service_id, pid):
        raise HTTPException(404, "服务不存在")
    ep = openapi_import_service.create_api_endpoint(db, project_id=pid, **body.model_dump())
    db.commit()
    db.refresh(ep)
    return R.ok(ApiEndpointOut.model_validate(ep))


@router.put("/endpoints/{endpoint_id}", response_model=R[ApiEndpointOut], summary="更新接口资产")
def update_endpoint(
    endpoint_id: int,
    body: ApiEndpointUpdate,
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    ep = openapi_import_service.get_project_endpoint(db, endpoint_id, pid)
    if not ep:
        raise HTTPException(404, "接口资产不存在")
    if body.service_id is not None and not openapi_import_service.get_project_service(db, body.service_id, pid):
        raise HTTPException(404, "服务不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(ep, k, v)
    db.commit()
    db.refresh(ep)
    return R.ok(ApiEndpointOut.model_validate(ep))


@router.delete("/endpoints/{endpoint_id}", response_model=R[dict], summary="删除接口资产")
def delete_endpoint(
    endpoint_id: int,
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    """Delete an endpoint unless an active-project test case still references it."""
    pid = _current_project_id(current)
    ep = openapi_import_service.get_project_endpoint(db, endpoint_id, pid)
    if not ep:
        raise HTTPException(404, "接口资产不存在")

    if openapi_import_service.endpoint_referenced_by_case(db, pid, endpoint_id):
        raise HTTPException(409, "接口资产仍被测试用例引用，无法删除")

    db.delete(ep)
    db.commit()
    return R.ok({"id": endpoint_id})


# ═══════════════════════════════════════════════════════
# OpenAPI 导入
# ═══════════════════════════════════════════════════════

@router.post("/import/preview", response_model=R[dict], summary="导入预览")
def import_preview(
    body: OpenApiImportPreviewRequest,
    current: CurrentUser = Depends(require_permission("apitest:import")),
    db: Session = Depends(get_db),
):
    """解析 OpenAPI/Swagger spec，返回接口列表预览。"""
    from app.services.openapi_import_service import preview_openapi_import_with_db

    pid = _current_project_id(current)
    spec = _resolve_spec(body.source_type, body.source_ref, body.spec_content)
    if not spec:
        raise HTTPException(400, "无法解析 OpenAPI 文档，请检查输入内容")

    result = preview_openapi_import_with_db(db, spec, project_id=pid, service_name=body.service_name)
    return R.ok(result)


@router.post("/import/confirm", response_model=R[dict], summary="确认导入")
def import_confirm(
    body: OpenApiImportConfirmRequest,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("apitest:import")),
    db: Session = Depends(get_db),
):
    """确认导入 OpenAPI 接口到资产库。"""
    from app.services.openapi_import_service import confirm_openapi_import

    pid = _current_project_id(current)
    spec = _resolve_spec(body.source_type, body.source_ref, body.spec_content)
    if not spec:
        raise HTTPException(400, "无法解析 OpenAPI 文档")

    result = confirm_openapi_import(
        db, spec,
        project_id=pid,
        service_name=body.service_name,
        source_ref=body.source_ref,
        source_type=body.source_type,
    )

    # M1 入库 hook：接口导入 → 沉淀为知识源（api_schema 切片）
    background_tasks.add_task(
        ingest_service.ingest_api_import_in_new_session,
        pid, result["batch_id"], body.service_name,
    )

    # 可选：导入后批量生成用例
    generated_case_ids: list[int] = []
    if body.generate_cases:
        generated, case_ids = _batch_generate_for_endpoints(db, result["batch_id"], pid)
        result["generated_case_count"] = generated
        generated_case_ids = case_ids
        # 生成的用例一并入库（test_case 切片）
        if case_ids:
            background_tasks.add_task(
                ingest_service.ingest_test_cases_in_new_session, pid, case_ids,
            )
    else:
        result["generated_case_count"] = 0

    # 可选：导入后自动创建测试计划并关联用例
    if body.create_plan and generated_case_ids:
        plan_name = body.plan_name.strip() or f"{body.service_name} 测试计划"
        result["created_plan"] = create_plan_with_cases(
            db,
            project_id=pid,
            name=plan_name,
            description=f"由 OpenAPI 导入自动创建 ({body.service_name})",
            creator_id=current.user.id if current.user else 0,
            case_ids=generated_case_ids,
        )

    return R.ok(result)
