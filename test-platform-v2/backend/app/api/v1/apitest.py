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
from app.services import api_task_worker

router = APIRouter(prefix="/apitest", tags=["接口测试"])


# ═══════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════

def _current_project_id(current: CurrentUser) -> int:
    """Derive current project from JWT token. Rejects missing project context."""
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


def _get_project_service(db: Session, service_id: int, project_id: int) -> ApiService | None:
    """Return a service only when it belongs to the active project."""
    return db.query(ApiService).filter(
        ApiService.id == service_id,
        ApiService.project_id == project_id,
    ).first()


def _get_project_endpoint(db: Session, endpoint_id: int, project_id: int) -> ApiEndpoint | None:
    """Return an endpoint only when it belongs to the active project."""
    return db.query(ApiEndpoint).filter(
        ApiEndpoint.id == endpoint_id,
        ApiEndpoint.project_id == project_id,
    ).first()


def _get_project_task(db: Session, task_id: int, project_id: int) -> ApiExecutionTask | None:
    """Return an execution task only when it belongs to the active project."""
    return db.query(ApiExecutionTask).filter(
        ApiExecutionTask.id == task_id,
        ApiExecutionTask.project_id == project_id,
    ).first()


def _endpoint_reference(endpoint_id: int) -> str:
    """Build the stable TestCase.api_spec_ref marker used by safe deletion."""
    return f"api_endpoint:{endpoint_id}"


def _safe_json(raw: str, default=None):
    if not raw or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _build_response_snapshot(result: dict) -> str:
    """构建结构化响应快照 JSON 字符串。"""
    snapshot = result.get("response_snapshot", {})
    if not snapshot:
        # 兼容旧版执行结果：从顶层字段构建
        raw_body = result.get("raw_body") or ""
        body_size = len(raw_body) if raw_body else 0
        preview_max = 4096
        body_preview = raw_body[:preview_max] if len(raw_body) > preview_max else raw_body
        snapshot = {
            "status_code": result.get("status_code"),
            "headers": result.get("response_headers", {}),
            "body_preview": body_preview,
            "body_size_bytes": body_size,
            "truncated": len(raw_body) > preview_max,
            "content_type": result.get("response_headers", {}).get("content-type", ""),
        }
    # Always ensure body_preview and truncated are populated
    if "body_preview" not in snapshot:
        snapshot["body_preview"] = ""
    if "truncated" not in snapshot:
        snapshot["truncated"] = False
    return json.dumps(snapshot, ensure_ascii=False, default=str)


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
    confirm_prod: bool = False  # 生产环境写操作必须为 True


@router.post("/api-execute", response_model=R[dict], summary="即时执行（调试）")
def api_quick_execute(
    body: QuickExecuteRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    """发送一个接口请求并返回响应+断言结果（不保存为用例）。

    生产环境写操作需要 apitest:execute_prod 权限 + confirm_prod=true。
    """
    request_def = {
        "method": body.method,
        "url": body.url,
        "headers": _safe_json(body.headers, {}),
        "body": body.body,
    }
    assertions = _safe_json(body.assertions, [])

    # 判断用户是否有生产环境执行权限
    has_execute_prod = current.is_super or "apitest:execute_prod" in current.permissions

    try:
        result = quick_execute(
            db, request_def,
            assertions=assertions,
            environment_id=body.environment_id,
            dataset_id=body.dataset_id,
            confirm_prod=body.confirm_prod,
            has_execute_prod=has_execute_prod,
        )
    except Exception as e:
        return R(code=1, msg=f"执行失败: {e}")

    return R.ok(result)


# ═══════════════════════════════════════════════════════
# 服务管理
# ═══════════════════════════════════════════════════════

@router.get("/services", response_model=R[list[ApiServiceOut]], summary="服务列表")
def list_services(
    current: CurrentUser = Depends(require_permission("apitest:view")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    rows = db.query(ApiService).filter_by(project_id=pid).order_by(ApiService.name).all()
    return R.ok([ApiServiceOut.model_validate(r) for r in rows])


@router.post("/services", response_model=R[ApiServiceOut], summary="创建服务")
def create_service(
    body: ApiServiceCreate,
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    svc = ApiService(project_id=pid, **body.model_dump())
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
    pid = _current_project_id(current)
    svc = _get_project_service(db, service_id, pid)
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
    svc = _get_project_service(db, service_id, pid)
    if not svc:
        raise HTTPException(404, "服务不存在")

    referenced = db.query(ApiEndpoint.id).filter(ApiEndpoint.service_id == service_id).first()
    if referenced:
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
    q = db.query(ApiEndpoint).filter_by(project_id=pid)
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
    current: CurrentUser = Depends(require_permission("apitest:asset_manage")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    if not _get_project_service(db, body.service_id, pid):
        raise HTTPException(404, "服务不存在")
    ep = ApiEndpoint(project_id=pid, **body.model_dump())
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
    pid = _current_project_id(current)
    ep = _get_project_endpoint(db, endpoint_id, pid)
    if not ep:
        raise HTTPException(404, "接口资产不存在")
    if body.service_id is not None and not _get_project_service(db, body.service_id, pid):
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
    from app.models.test_case import TestCase

    pid = _current_project_id(current)
    ep = _get_project_endpoint(db, endpoint_id, pid)
    if not ep:
        raise HTTPException(404, "接口资产不存在")

    referenced = db.query(TestCase.id).filter(
        TestCase.project_id == pid,
        TestCase.api_spec_ref == _endpoint_reference(endpoint_id),
    ).first()
    if referenced:
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
    from app.services.knowledge import ingest_service
    background_tasks.add_task(
        ingest_service.ingest_api_import_in_new_session,
        pid, result["batch_id"], body.service_name,
    )

    # 可选：导入后批量生成用例
    if body.generate_cases:
        generated, case_ids = _batch_generate_for_endpoints(db, result["batch_id"], pid)
        result["generated_case_count"] = generated
        # 生成的用例一并入库（test_case 切片）
        if case_ids:
            background_tasks.add_task(
                ingest_service.ingest_test_cases_in_new_session, pid, case_ids,
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

    endpoints = db.query(ApiEndpoint).filter_by(
        import_batch_id=batch_id,
        project_id=project_id,
    ).all()
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
    current: CurrentUser = Depends(require_permission("apitest:generate")),
    db: Session = Depends(get_db),
):
    """基于接口定义生成测试用例。"""
    from app.services.api_case_generation_service import generate_cases_from_endpoint

    pid = _current_project_id(current)

    # 获取 endpoint 数据
    if body.endpoint_id:
        ep = _get_project_endpoint(db, body.endpoint_id, pid)
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
            tc = _create_test_case_from_generated(db, pid, c, body.endpoint_id)
            imported_ids.append(tc.id)
        db.commit()
        # M1 入库 hook：生成用例 → 沉淀为知识切片
        if imported_ids:
            from app.services.knowledge import ingest_service
            background_tasks.add_task(
                ingest_service.ingest_test_cases_in_new_session, pid, imported_ids.copy(),
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
    current: CurrentUser = Depends(require_permission("apitest:generate")),
    db: Session = Depends(get_db),
):
    """批量多个接口生成测试用例。"""
    from app.services.api_case_generation_service import generate_cases_from_endpoint

    pid = _current_project_id(current)
    total_generated = 0
    all_imported_ids = []
    errors = []

    for ep_id in body.endpoint_ids:
        ep = _get_project_endpoint(db, ep_id, pid)
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
                tc = _create_test_case_from_generated(db, pid, c, ep_id)
                all_imported_ids.append(tc.id)

    db.commit()
    # M1 入库 hook：批量生成用例 → 沉淀为知识切片
    if all_imported_ids:
        from app.services.knowledge import ingest_service
        background_tasks.add_task(
            ingest_service.ingest_test_cases_in_new_session, pid, all_imported_ids.copy(),
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
        api_spec_ref=_endpoint_reference(endpoint_id) if endpoint_id else "",
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
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """从用例列表创建批量执行任务。

    任务创建后状态为 pending，由持久化 task_worker 后台轮询认领执行。
    接口立即返回，不等待用例执行完成。

    生产环境任务需要 apitest:execute_prod 权限 + confirm_prod=true。
    """
    from app.models.test_case import TestCase
    from app.models.environment import Environment

    pid = _current_project_id(current)
    task_id_str = f"API-{uuid.uuid4().hex[:8].upper()}"

    # 验证用例存在且为 API 类型
    cases = db.query(TestCase).filter(
        TestCase.id.in_(body.case_ids),
        TestCase.project_id == pid,
        TestCase.case_type == "api",
    ).all()

    if len(cases) != len(body.case_ids):
        raise HTTPException(400, "部分用例不存在或不是 API 类型")

    # 生产环境保护检查：若目标环境为 prod，验证权限和二次确认
    has_execute_prod = current.is_super or "apitest:execute_prod" in current.permissions
    if body.environment_id:
        env = db.get(Environment, body.environment_id)
        if env and env.env_type == "prod":
            if not has_execute_prod:
                raise HTTPException(403, "生产环境执行任务需要 apitest:execute_prod 权限")
            if not body.confirm_prod:
                raise HTTPException(400, "生产环境执行任务需要 confirm_prod=true 确认")

    task = ApiExecutionTask(
        project_id=pid,
        task_id=task_id_str,
        name=body.name,
        environment_id=body.environment_id,
        service_id=body.service_id,
        status="pending",
        total=len(cases),
        creator_id=current.user.id if current.user else 0,
        confirm_prod=body.confirm_prod,
    )
    db.add(task)
    db.flush()

    # 创建任务明细
    for case in cases:
        item = ApiExecutionTaskItem(task_id=task.id, case_id=case.id)
        db.add(item)

    db.commit()
    db.refresh(task)

    # 启动 worker 并唤醒以立即处理新任务
    api_task_worker.ensure_processor_running()
    api_task_worker.kick()

    return R.ok(ApiTaskOut.model_validate(task))


@router.get("/tasks", response_model=R[dict], summary="任务列表")
def list_tasks(
    service_id: int | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    pid = _current_project_id(current)
    q = db.query(ApiExecutionTask).filter_by(project_id=pid)
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
    pid = _current_project_id(current)
    if task.project_id != pid:
        raise HTTPException(403, "无权访问该任务")

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
    """设置 cancel_requested 标记，由 worker 在下一条 item 执行前检查并终止。"""
    task = db.get(ApiExecutionTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    pid = _current_project_id(current)
    if task.project_id != pid:
        raise HTTPException(403, "无权访问该任务")
    if task.status not in ("pending", "running"):
        raise HTTPException(400, "只能取消 pending 或 running 状态的任务")
    task.cancel_requested = True
    db.commit()
    # 唤醒 worker 以立即处理取消
    api_task_worker.kick()
    return R.ok({"status": "cancelling", "task_id": task.id})


@router.post("/tasks/{task_id}/retry-failed", response_model=R[dict], summary="重跑失败用例")
def retry_failed(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """为原任务中所有失败项创建新的重试任务（trigger_type=retry_failed）。

    原任务不受影响；新任务仅包含失败项的 case_id。
    """
    pid = _current_project_id(current)
    task = db.get(ApiExecutionTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.project_id != pid:
        raise HTTPException(403, "无权访问该任务")

    failed_items = db.query(ApiExecutionTaskItem).filter_by(
        task_id=task.id, status="failed"
    ).all()

    if not failed_items:
        raise HTTPException(400, "没有失败的用例需要重跑")

    # 收集失败用例的 case_id（去重）
    failed_case_ids = list({it.case_id for it in failed_items})

    # 创建新任务
    retry_task_id_str = f"API-{uuid.uuid4().hex[:8].upper()}"
    new_task = ApiExecutionTask(
        project_id=pid,
        task_id=retry_task_id_str,
        name=f"{task.name} (失败重试)",
        environment_id=task.environment_id,
        service_id=task.service_id,
        status="pending",
        total=len(failed_case_ids),
        trigger_type="retry_failed",
        creator_id=current.user.id if current.user else 0,
    )
    db.add(new_task)
    db.flush()

    for cid in failed_case_ids:
        item = ApiExecutionTaskItem(task_id=new_task.id, case_id=cid)
        db.add(item)

    db.commit()
    db.refresh(new_task)

    # 唤醒 worker
    api_task_worker.ensure_processor_running()
    api_task_worker.kick()

    return R.ok({
        "new_task_id": new_task.id,
        "new_task_uid": retry_task_id_str,
        "retry_count": len(failed_case_ids),
        "original_task_id": task.id,
    })


@router.get("/tasks/{task_id}/items/{item_id}/curl", response_model=R[dict], summary="生成 curl 复现命令")
def get_curl_command(
    task_id: int,
    item_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """从请求快照生成等效 curl 命令，方便失败排查和复现。"""
    from app.services.api_execution_service import build_curl_command

    pid = _current_project_id(current)
    task = _get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")

    item = db.get(ApiExecutionTaskItem, item_id)
    if not item or item.task_id != task.id:
        raise HTTPException(404, "任务明细不存在")

    try:
        snapshot = json.loads(item.request_snapshot) if item.request_snapshot else {}
    except (json.JSONDecodeError, TypeError):
        snapshot = {}

    if not snapshot:
        raise HTTPException(400, "该执行记录无请求快照，无法生成 curl 命令")

    curl_cmd = build_curl_command(snapshot)
    return R.ok({"curl": curl_cmd, "snapshot": snapshot})


@router.get("/tasks/{task_id}/analysis", response_model=R[dict], summary="任务失败分析")
def analyze_task_failures(
    task_id: int,
    current: CurrentUser = Depends(require_permission("apitest:task")),
    db: Session = Depends(get_db),
):
    """对任务中所有失败项进行结构化分析，返回分类和修复建议。"""
    from app.services.failure_analyzer import analyze_api_failure

    pid = _current_project_id(current)
    task = _get_project_task(db, task_id, pid)
    if not task:
        raise HTTPException(404, "任务不存在")

    failed_items = db.query(ApiExecutionTaskItem).filter_by(
        task_id=task.id, status="failed"
    ).all()

    if not failed_items:
        return R.ok({"analyses": [], "summary": "没有失败项需要分析"})

    analyses = [analyze_api_failure(item) for item in failed_items]

    # 汇总分类
    categories: dict[str, int] = {}
    for a in analyses:
        cat = a["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return R.ok({
        "total_failed": len(failed_items),
        "categories": categories,
        "analyses": analyses,
    })
