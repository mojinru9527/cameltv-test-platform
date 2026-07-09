"""接口测试 API 路由 — 资产/导入/用例生成/执行/批量任务。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.models.api_asset import ApiEndpoint, ApiExecutionTask, ApiExecutionTaskItem, ApiService
from app.schemas.api_asset import (
    ApiEndpointCreate, ApiEndpointOut, ApiEndpointUpdate,
    ApiServiceCreate, ApiServiceOut, ApiServiceUpdate,
    ApiTaskCreateRequest, ApiTaskDetailOut, ApiTaskItemOut, ApiTaskOut,
    BatchGenerateRequest, GenerateApiCasesRequest,
    OpenApiImportConfirmRequest, OpenApiImportPreviewRequest,
)
from app.schemas.common import R, Page
from app.services.api_execution_service import quick_execute

router = APIRouter(prefix="/apitest", tags=["接口测试"])


# ═══════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════

def _safe_json(raw: str, default=None):
    if not raw or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _paginate(query, db: Session, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ═══════════════════════════════════════════════════════
# 即时执行（保留原有功能）
# ═══════════════════════════════════════════════════════

class QuickExecuteRequest(BaseModel):
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    url: str = Field(..., min_length=1)
    headers: str = Field(default="{}")
    body: str = Field(default="")
    assertions: str = Field(default="[]")
    environment_id: int | None = None
    dataset_id: int | None = None


@router.post("/api-execute", response_model=R[dict], summary="即时执行（调试）")
def api_quick_execute(
    body: QuickExecuteRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """发送一个接口请求并返回响应+断言结果（不保存为用例）。"""
    request_def = {
        "method": body.method,
        "url": body.url,
        "headers": _safe_json(body.headers, {}),
        "body": body.body,
    }
    assertions = _safe_json(body.assertions, [])

    try:
        result = quick_execute(
            db, request_def,
            assertions=assertions,
            environment_id=body.environment_id,
            dataset_id=body.dataset_id,
        )
    except Exception as e:
        return R(code=1, msg=f"执行失败: {e}")

    return R.ok(result)


# ═══════════════════════════════════════════════════════
# 服务管理
# ═══════════════════════════════════════════════════════

@router.get("/services", response_model=R[list[ApiServiceOut]], summary="服务列表")
def list_services(
    project_id: int = Query(..., description="项目 ID"),
    current: CurrentUser = Depends(require_permission("apitest:view")),
    db: Session = Depends(get_db),
):
    rows = db.query(ApiService).filter_by(project_id=project_id).order_by(ApiService.name).all()
    return R.ok([ApiServiceOut.model_validate(r) for r in rows])


@router.post("/services", response_model=R[ApiServiceOut], summary="创建服务")
def create_service(
    body: ApiServiceCreate,
    project_id: int = Query(..., description="项目 ID"),
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    svc = ApiService(project_id=project_id, **body.model_dump())
    db.add(svc)
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
    svc = db.get(ApiService, service_id)
    if not svc:
        raise HTTPException(404, "服务不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(svc, k, v)
    db.commit()
    db.refresh(svc)
    return R.ok(ApiServiceOut.model_validate(svc))


# ═══════════════════════════════════════════════════════
# 接口资产管理
# ═══════════════════════════════════════════════════════

@router.get("/endpoints", response_model=R[dict], summary="接口资产列表（分页）")
def list_endpoints(
    project_id: int = Query(...),
    service_id: int | None = Query(None),
    module: str | None = Query(None),
    method: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("apitest:view")),
    db: Session = Depends(get_db),
):
    q = db.query(ApiEndpoint).filter_by(project_id=project_id)
    if service_id:
        q = q.filter_by(service_id=service_id)
    if module:
        q = q.filter_by(module=module)
    if method:
        q = q.filter_by(method=method.upper())
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (ApiEndpoint.path.ilike(like)) | (ApiEndpoint.summary.ilike(like))
        )
    q = q.order_by(ApiEndpoint.module, ApiEndpoint.path)

    result = _paginate(q, db, page, page_size)
    result["items"] = [ApiEndpointOut.model_validate(r) for r in result["items"]]
    return R.ok(result)


@router.post("/endpoints", response_model=R[ApiEndpointOut], summary="手动创建接口资产")
def create_endpoint(
    body: ApiEndpointCreate,
    project_id: int = Query(...),
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    ep = ApiEndpoint(project_id=project_id, **body.model_dump())
    db.add(ep)
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
    ep = db.get(ApiEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(404, "接口资产不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(ep, k, v)
    db.commit()
    db.refresh(ep)
    return R.ok(ApiEndpointOut.model_validate(ep))


# ═══════════════════════════════════════════════════════
# OpenAPI 导入
# ═══════════════════════════════════════════════════════

@router.post("/import/preview", response_model=R[dict], summary="导入预览")
def import_preview(
    body: OpenApiImportPreviewRequest,
    project_id: int = Query(...),
    current: CurrentUser = Depends(require_permission("apitest:import")),
    db: Session = Depends(get_db),
):
    """解析 OpenAPI/Swagger spec，返回接口列表预览。"""
    from app.services.openapi_import_service import preview_openapi_import_with_db

    spec = _resolve_spec(body.source_type, body.source_ref, body.spec_content)
    if not spec:
        raise HTTPException(400, "无法解析 OpenAPI 文档，请检查输入内容")

    result = preview_openapi_import_with_db(db, spec, project_id=project_id, service_name=body.service_name)
    return R.ok(result)


@router.post("/import/confirm", response_model=R[dict], summary="确认导入")
def import_confirm(
    body: OpenApiImportConfirmRequest,
    background_tasks: BackgroundTasks,
    project_id: int = Query(...),
    current: CurrentUser = Depends(require_permission("apitest:import")),
    db: Session = Depends(get_db),
):
    """确认导入 OpenAPI 接口到资产库。"""
    from app.services.openapi_import_service import confirm_openapi_import

    spec = _resolve_spec(body.source_type, body.source_ref, body.spec_content)
    if not spec:
        raise HTTPException(400, "无法解析 OpenAPI 文档")

    result = confirm_openapi_import(
        db, spec,
        project_id=project_id,
        service_name=body.service_name,
        source_ref=body.source_ref,
        source_type=body.source_type,
    )

    # M1 入库 hook：接口导入 → 沉淀为知识源（api_schema 切片）
    from app.services.knowledge import ingest_service
    background_tasks.add_task(
        ingest_service.ingest_api_import_in_new_session,
        project_id, result["batch_id"], body.service_name,
    )

    # 可选：导入后批量生成用例
    if body.generate_cases:
        generated, case_ids = _batch_generate_for_endpoints(db, result["batch_id"], project_id)
        result["generated_case_count"] = generated
        # 生成的用例一并入库（test_case 切片）
        if case_ids:
            background_tasks.add_task(
                ingest_service.ingest_test_cases_in_new_session, project_id, case_ids,
            )
    else:
        result["generated_case_count"] = 0

    return R.ok(result)


def _resolve_spec(source_type: str, source_ref: str, spec_content: str | None) -> dict | None:
    """从不同来源解析 OpenAPI spec 为 dict。"""
    import yaml as _yaml

    raw = spec_content or ""

    # URL 导入
    if source_type == "openapi_url" and source_ref:
        try:
            import httpx
            resp = httpx.get(source_ref, timeout=30)
            resp.raise_for_status()
            raw = resp.text
        except Exception:
            return None

    # 文件导入 — raw 已在 spec_content 中
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
    from app.services.api_case_generation_service import generate_cases_from_endpoint

    endpoints = db.query(ApiEndpoint).filter_by(import_batch_id=batch_id).all()
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
            tc = _create_test_case_from_generated(db, project_id, c, ep.id)
            case_ids.append(tc.id)
            count += 1
    db.commit()
    return count, case_ids


# ═══════════════════════════════════════════════════════
# 用例生成
# ═══════════════════════════════════════════════════════

@router.post("/cases/generate", response_model=R[dict], summary="单接口生成用例")
def generate_cases(
    body: GenerateApiCasesRequest,
    background_tasks: BackgroundTasks,
    project_id: int = Query(...),
    current: CurrentUser = Depends(require_permission("apitest:generate")),
    db: Session = Depends(get_db),
):
    """基于接口定义生成测试用例。"""
    from app.services.api_case_generation_service import generate_cases_from_endpoint

    # 获取 endpoint 数据
    if body.endpoint_id:
        ep = db.get(ApiEndpoint, body.endpoint_id)
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
            tc = _create_test_case_from_generated(db, project_id, c, body.endpoint_id)
            imported_ids.append(tc.id)
        db.commit()
        # M1 入库 hook：生成用例 → 沉淀为知识切片
        if imported_ids:
            from app.services.knowledge import ingest_service
            background_tasks.add_task(
                ingest_service.ingest_test_cases_in_new_session, project_id, imported_ids.copy(),
            )

    return R.ok({
        "cases": cases,
        "total": len(cases),
        "imported_case_ids": imported_ids,
    })


@router.post("/cases/batch-generate", response_model=R[dict], summary="批量生成用例")
def batch_generate_cases(
    body: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
    project_id: int = Query(...),
    current: CurrentUser = Depends(require_permission("apitest:generate")),
    db: Session = Depends(get_db),
):
    """批量多个接口生成测试用例。"""
    from app.services.api_case_generation_service import generate_cases_from_endpoint

    total_generated = 0
    all_imported_ids = []
    errors = []

    for ep_id in body.endpoint_ids:
        ep = db.get(ApiEndpoint, ep_id)
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
                tc = _create_test_case_from_generated(db, project_id, c, ep_id)
                all_imported_ids.append(tc.id)

    db.commit()
    # M1 入库 hook：批量生成用例 → 沉淀为知识切片
    if all_imported_ids:
        from app.services.knowledge import ingest_service
        background_tasks.add_task(
            ingest_service.ingest_test_cases_in_new_session, project_id, all_imported_ids.copy(),
        )

    return R.ok({
        "total_generated": total_generated,
        "imported_case_ids": all_imported_ids,
        "errors": errors,
    })


def _create_test_case_from_generated(db: Session, project_id: int, case_data: dict, endpoint_id: int | None):
    """将生成的用例数据写入 TestCase 表。"""
    from app.models.test_case import TestCase
    import json as _json

    tc = TestCase(
        project_id=project_id,
        title=case_data.get("title", ""),
        domain=case_data.get("domain", "接口测试"),
        module=case_data.get("module", ""),
        case_type="api",
        priority=case_data.get("priority", "P1"),
        preconditions=case_data.get("preconditions", ""),
        steps=_json.dumps(case_data.get("steps", []), ensure_ascii=False),
        expected_result=case_data.get("expected_result", ""),
        api_method=case_data.get("api_method", "GET"),
        api_endpoint=case_data.get("api_endpoint", ""),
        api_headers=_json.dumps(case_data.get("api_headers", {}), ensure_ascii=False),
        api_body=case_data.get("api_body", ""),
        api_assertions=_json.dumps(case_data.get("api_assertions", []), ensure_ascii=False),
        status="draft",
        source="ai_generated",
        tags=_json.dumps(case_data.get("tags", []), ensure_ascii=False),
    )
    db.add(tc)
    db.flush()
    return tc


# ═══════════════════════════════════════════════════════
# 批量执行任务
# ═══════════════════════════════════════════════════════

@router.post("/tasks", response_model=R[ApiTaskOut], summary="创建执行任务")
def create_task(
    body: ApiTaskCreateRequest,
    project_id: int = Query(...),
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """从用例列表创建批量执行任务。执行通过 BackgroundTasks 异步进行。"""
    from app.models.test_case import TestCase

    task_id_str = f"API-{uuid.uuid4().hex[:8].upper()}"

    # 验证用例存在且为 API 类型
    cases = db.query(TestCase).filter(
        TestCase.id.in_(body.case_ids),
        TestCase.project_id == project_id,
        TestCase.case_type == "api",
    ).all()

    if len(cases) != len(body.case_ids):
        raise HTTPException(400, "部分用例不存在或不是 API 类型")

    task = ApiExecutionTask(
        project_id=project_id,
        task_id=task_id_str,
        name=body.name,
        environment_id=body.environment_id,
        service_id=body.service_id,
        total=len(cases),
        creator_id=current.user.id if current.user else 0,
    )
    db.add(task)
    db.flush()

    # 创建任务明细
    for case in cases:
        item = ApiExecutionTaskItem(task_id=task.id, case_id=case.id)
        db.add(item)

    db.commit()

    # 通过 BackgroundTasks 异步执行（不阻塞请求线程）
    background_tasks.add_task(_execute_task_async, task.id, project_id)

    db.refresh(task)
    return R.ok(ApiTaskOut.model_validate(task))


def _execute_task_async(task_id: int, project_id: int):
    """在独立 DB session 中执行批量任务（供 BackgroundTasks 调用）。
    必须使用独立的 SessionLocal()，因为 BackgroundTasks 在响应返回后执行，
    原请求的 db session 可能已关闭。
    """
    from app.core.db import SessionLocal
    from app.models.test_case import TestCase
    from app.services.api_execution_service import execute_api_case

    db = SessionLocal()
    try:
        task = db.get(ApiExecutionTask, task_id)
        if not task:
            return

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        items = db.query(ApiExecutionTaskItem).filter_by(task_id=task.id).all()
        passed = 0
        failed = 0

        for item in items:
            try:
                result = execute_api_case(
                    db, item.case_id,
                    project_id=project_id,
                    environment_id=task.environment_id,
                )
                item.status = "passed" if result.get("all_pass", False) else "failed"
                item.duration_ms = result.get("duration_ms", 0)
                item.request_snapshot = json.dumps(result.get("request_snapshot", {}), ensure_ascii=False)
                item.response_snapshot = json.dumps({
                    "status_code": result.get("status_code"),
                    "response_body": result.get("response_body"),
                }, ensure_ascii=False, default=str)
                item.assertion_results = json.dumps(result.get("assertions", []), ensure_ascii=False)
                if result.get("error"):
                    item.error_message = result["error"]

                if item.status == "passed":
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                item.status = "failed"
                item.error_message = str(e)
                failed += 1

        task.passed = passed
        task.failed = failed
        task.skipped = task.total - passed - failed
        task.status = "success" if failed == 0 else "failed"
        task.finished_at = datetime.now(timezone.utc)
        db.commit()

        # M1 入库 hook：有失败项时 → 沉淀为知识切片（用于后续影响分析 & Agent 学习）
        if failed > 0:
            from app.services.knowledge import ingest_service
            ingest_service.ingest_execution_failure_in_new_session(project_id, task_id)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Background task execution failed: task_id=%s", task_id)
    finally:
        db.close()


@router.get("/tasks", response_model=R[dict], summary="任务列表")
def list_tasks(
    project_id: int = Query(...),
    service_id: int | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    q = db.query(ApiExecutionTask).filter_by(project_id=project_id)
    if service_id:
        q = q.filter_by(service_id=service_id)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(ApiExecutionTask.created_at.desc())

    result = _paginate(q, db, page, page_size)
    result["items"] = [ApiTaskOut.model_validate(r) for r in result["items"]]
    return R.ok(result)


@router.get("/tasks/{task_id}", response_model=R[ApiTaskDetailOut], summary="任务详情")
def get_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    task = db.get(ApiExecutionTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    items = db.query(ApiExecutionTaskItem).filter_by(task_id=task.id).all()
    detail = ApiTaskDetailOut(
        **ApiTaskOut.model_validate(task).model_dump(),
        items=[ApiTaskItemOut.model_validate(it) for it in items],
    )
    return R.ok(detail)


@router.post("/tasks/{task_id}/cancel", response_model=R[dict], summary="取消任务")
def cancel_task(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    task = db.get(ApiExecutionTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status not in ("pending", "running"):
        raise HTTPException(400, "只能取消 pending 或 running 状态的任务")
    task.status = "cancelled"
    task.finished_at = datetime.now(timezone.utc)
    db.commit()
    return R.ok({"status": "cancelled"})
