"""Open API for CI/CD integration — authenticated via API Token."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.config import settings
from app.core.exceptions import APIException
from app.core.execution_status import canonical_exec_status
from app.core.rate_limit import open_api_limiter
from app.schemas.common import R
from app.services import test_plan_service, token_service, ui_test_service

if TYPE_CHECKING:
    from app.models.api_token import ApiToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/open", tags=["开放API"])

# Allow-listed health check path (no auth required)
_HEALTH_PATH = "/open/health"


def _check_rate_limit(token: "ApiToken") -> None:
    """Enforce 60 req/min per token. Raises 429 if exceeded."""
    allowed, wait = open_api_limiter.is_allowed(token.token_hash)
    if not allowed:
        raise APIException(
            code=429,
            msg=f"请求过于频繁，请 {wait}s 后重试 (限制: 60次/分钟)",
            http_status=429,
        )


def verify_api_token(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> "ApiToken | None":
    """Validate `Bearer tpat_xxx` against stored hashes."""
    if not authorization or not authorization.startswith("Bearer "):
        raise APIException(code=401, msg="缺少 API Token (Authorization: Bearer tpat_xxx)", http_status=401)

    plain = authorization[len("Bearer "):]
    token_hash = hashlib.sha256(plain.encode()).hexdigest()

    # 鉴权核心查询收敛至 token_service（Batch 182/C181-1）
    row = token_service.verify_token_hash(db, token_hash)
    if not row:
        raise APIException(code=401, msg="无效或已禁用的 API Token", http_status=401)

    # Rate limit check (after auth so we know which token)
    _check_rate_limit(row)

    return row


# ── Health ────────────────────────────────────────────

@router.get("/health", summary="连通性检查")
def health_check():
    """轻量健康检查，无需鉴权。CI 可在触发前调用以验证 API 可达。"""
    return R.ok({"status": "ok", "version": "2.3.0"})


@router.post("/plans/{plan_id}/trigger", response_model=R[dict], summary="CI 触发测试计划执行")
def ci_trigger_plan(
    plan_id: int,
    req: Request,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI (Jenkins/GitHub Actions) 通过 API Token 触发测试计划。

    触发后返回执行摘要。结果可通过 GET /open/runs/{run_id} 查询。
    """
    plan, executed = test_plan_service.trigger_plan_from_ci(
        db, plan_id, token.project_id, token_name=token.name
    )
    if not plan:
        raise APIException(code=404, msg="计划不存在")

    # Update token last_used
    token.last_used_at = datetime.now(timezone.utc)

    db.commit()

    # Background notification
    try:
        from app.services.notify_service import notify_sync
        notify_sync(db, token.project_id, "plan_done", {
            "plan_name": plan.name,
            "result_summary": f"CI 触发 {executed} 条用例已入队",
            "link": "",
        })
    except Exception:
        logger.exception("CI 触发通知失败: plan_id=%s", plan_id)

    return R.ok({
        "triggered": True,
        "plan_id": plan_id,
        "plan_name": plan.name,
        "cases_queued": executed,
        "triggered_by": token.name,
    })


@router.get("/runs/{run_id}", response_model=R[dict], summary="查询执行结果")
def ci_get_run(
    run_id: int,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI 查询某次执行的状态与结果。"""
    exec_row = test_plan_service.get_execution(db, run_id)
    if not exec_row:
        raise APIException(code=404, msg="执行记录不存在")

    # Project isolation via plan_case → plan
    plan_case = test_plan_service.get_plan_case(db, exec_row.plan_case_id)
    if not plan_case or plan_case.plan.project_id != token.project_id:
        raise APIException(code=403, msg="无权访问此执行记录")

    return R.ok({
        "run_id": exec_row.id,
        "plan_case_id": exec_row.plan_case_id,
        "case_id": plan_case.case_id,
        "status": exec_row.status,
        "actual_result": exec_row.actual_result,
        "notes": exec_row.notes,
        "trace_id": exec_row.trace_id,
        "executed_at": exec_row.executed_at.isoformat() if exec_row.executed_at else None,
    })


@router.post("/results", response_model=R[dict], summary="回写执行结果")
def ci_post_results(
    body: dict,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI 回写执行结果 (status, actual_result, trace_id, notes)。

    Body: { run_id: int, status: str, actual_result?: str, trace_id?: str, notes?: str }
    """
    run_id = body.get("run_id")
    if not run_id:
        raise APIException(code=400, msg="缺少 run_id")

    exec_row = test_plan_service.get_execution(db, run_id)
    if not exec_row:
        raise APIException(code=404, msg="执行记录不存在")

    # Project isolation
    plan_case = test_plan_service.get_plan_case(db, exec_row.plan_case_id)
    if not plan_case or plan_case.plan.project_id != token.project_id:
        raise APIException(code=403, msg="无权访问此执行记录")

    # Update fields
    # Batch 182（P1-06）：接受新旧双值（CI 旧脚本传 pass/fail/skip/block），规范化后落库
    if "status" in body:
        valid_statuses = {"pass", "fail", "skip", "block", "pending",
                          "passed", "failed", "skipped", "blocked", "running", "cancelled"}
        if body["status"] not in valid_statuses:
            raise APIException(code=400, msg=f"无效状态值，允许: {', '.join(sorted(valid_statuses))}")
        canonical = canonical_exec_status(body["status"])
        exec_row.status = canonical
        # Also update plan_case last_status
        plan_case.last_status = canonical
        plan_case.last_executed_at = datetime.now(timezone.utc)

    if "actual_result" in body:
        exec_row.actual_result = body["actual_result"]
    if "trace_id" in body:
        exec_row.trace_id = body["trace_id"]
    if "notes" in body:
        exec_row.notes = body["notes"]

    exec_row.executed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(exec_row)

    # Notify on terminal status（Batch 182：接受新旧双值）
    if canonical_exec_status(body.get("status", "")) in ("passed", "failed"):
        try:
            from app.services.notify_service import notify_sync
            notify_sync(db, token.project_id, "plan_done", {
                "plan_name": getattr(plan_case.plan, "name", ""),
                "result_summary": f"执行 #{run_id}: {body['status']}",
                "link": "",
            })
        except Exception:
            logger.exception("CI 结果回写通知失败: run_id=%s", getattr(exec_row, "id", None))

    return R.ok({
        "run_id": exec_row.id,
        "status": exec_row.status,
        "updated": True,
    })


# ── UI 测试触发 ────────────────────────────────────────

@router.post("/ui-tests/{job_id}/trigger", response_model=R[dict], summary="CI 触发 UI 自动化测试")
def ci_trigger_ui_test(
    job_id: int,
    req: Request,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI (Jenkins/GitHub Actions) 通过 API Token 触发 UI 自动化任务。

    返回 run 记录，可通过轮询 GET /api/v1/open/ui-tests/runs/{run_id} 查询状态。
    """
    try:
        job, run, pw_error = ui_test_service.trigger_ui_test_from_ci(
            db, job_id, token.project_id, token_name=token.name
        )
    except ValueError as e:
        raise APIException(code=400, msg=str(e))
    if job is None:
        raise APIException(code=404, msg="UI 测试任务不存在")

    # Update token last_used
    token.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)

    # 后台执行 (仅当 Playwright 可用)
    if pw_error is None:
        try:
            # Batch 179（FIX-173-P2-05）：统一走 ui_runner_queue 线程池入口，
            # 移除 open_api 专属裸线程（此前 UI 执行存在 三套入口并存 的调度冗余）。
            from app.services.ui_runner_queue import enqueue_run
            enqueue_run(run.id, job_id, token.project_id)
        except Exception:
            logger.exception("UI run 入队失败: run_id=%s job_id=%s", run.id, job_id)

    return R.ok({
        "triggered": True,
        "job_id": job_id,
        "job_name": job.name,
        "run_id": run.id,
        "run_status": run.status,
        "triggered_by": token.name,
    })


@router.get("/ui-tests/runs/{run_id}", response_model=R[dict], summary="CI 查询 UI 测试运行状态")
def ci_get_ui_run(
    run_id: int,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """外部 CI 查询 UI 测试运行的状态与结果。"""
    run = ui_test_service.get_run_orm(db, run_id)
    if not run:
        raise APIException(code=404, msg="运行记录不存在")

    # Project isolation via job
    job = ui_test_service.get_job_orm(db, run.job_id)
    if not job or job.project_id != token.project_id:
        raise APIException(code=403, msg="无权访问此运行记录")

    import json as _json
    result = {}
    try:
        result = _json.loads(run.result) if run.result else {}
    except (_json.JSONDecodeError, TypeError):
        logger.warning("执行结果 JSON 解析失败，按空结果处理: run_id=%s", run.id)

    return R.ok({
        "run_id": run.id,
        "job_id": run.job_id,
        "job_name": job.name,
        "status": run.status,
        "result": result,
        "error_message": run.error_message,
        "base_url": run.base_url,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    })


# ── 质量门禁检查 (CI/CD) ──────────────────────────────

@router.get("/reports/{report_id}/gate/check", summary="CI/CD 质量门禁检查")
def ci_check_report_gate(
    report_id: int,
    token: "ApiToken" = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    """CI/CD pipeline 质量门禁检查（API Token 鉴权）。

    门禁不通过时返回 HTTP 409 Conflict 阻止构建流水线。
    返回: {"blocked": bool, "details": [...], "gate_status": "pass"|"fail"|"warn"}
    """
    from fastapi.responses import JSONResponse

    from app.services.report_service import get_report_gate

    gate = get_report_gate(db, report_id, token.project_id)
    if not gate:
        raise APIException(code=404, msg="报告不存在")

    status = gate.get("gate_status", "unknown")
    details = gate.get("gate_details", [])
    blocked = status == "fail"

    if blocked:
        return JSONResponse(
            status_code=409,
            content={"blocked": True, "details": details, "gate_status": status},
        )
    return {"blocked": False, "details": details, "gate_status": status}


# ── DSH 测试 Agent 框架：知识查询面（L0/L1 对外只读/回写通道）─────
# knowledge-mcp 经本组端点访问知识中心（API Token 鉴权 + project 隔离）。
# 路由层禁 ORM（Batch 181 强制）：全部收敛至既有 service。

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
