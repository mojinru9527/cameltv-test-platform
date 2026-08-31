"""Playground API — test case → Playwright spec compile + execute."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.playground import (
    CompileRequest, CompileResponse, ExecuteRequest, ExecuteResponse,
    PlaygroundBatchCompileRequest, PlaygroundBatchCompileResponse,
    PlaygroundBatchRunRequest, PlaygroundBatchRunResponse,
)
from app.services.playground_service import (
    build_gherkin_from_case, compile_spec, execute_spec,
    compile_case_batch, get_case_by_case_id, run_case_batch,
)

router = APIRouter(prefix="/playground", tags=["Playground"])


@router.post("/batch-compile", response_model=PlaygroundBatchCompileResponse)
def batch_compile_endpoint(
    req: PlaygroundBatchCompileRequest,
    current: CurrentUser = Depends(require_permission("uitest:list")),
    db: Session = Depends(get_db),
) -> PlaygroundBatchCompileResponse:
    """从功能用例库批量编译 Playwright spec。"""
    return compile_case_batch(db, current.project_id or 0, req.case_ids)


@router.post("/batch-run", response_model=PlaygroundBatchRunResponse)
def batch_run_endpoint(
    req: PlaygroundBatchRunRequest,
    current: CurrentUser = Depends(require_permission("uitest:trigger")),
    db: Session = Depends(get_db),
) -> PlaygroundBatchRunResponse:
    """批量编译 + 执行功能用例，并把结果回填用例 / 回写 UI 任务。"""
    return run_case_batch(
        db,
        project_id=current.project_id or 0,
        creator_id=current.user.id if current.user else 0,
        case_ids=req.case_ids,
        write_back_to_ui=req.write_back_to_ui,
        timeout_ms=req.timeout_ms,
    )


@router.post("/compile", response_model=CompileResponse)
def compile_endpoint(
    req: CompileRequest,
    current: CurrentUser = Depends(require_permission("uitest:list")),
    db: Session = Depends(get_db),
) -> CompileResponse:
    """Compile a test case source (Gherkin/Markdown/plain) into a Playwright .spec.ts."""
    source = req.source
    if req.case_id:
        case = get_case_by_case_id(db, int(req.case_id), current.project_id)
        if not case:
            from app.core.exceptions import not_found
            raise not_found(f"功能用例 {req.case_id}")
        source = build_gherkin_from_case(case)
    return compile_spec(CompileRequest(source=source, source_type=req.source_type))


@router.post("/execute", response_model=ExecuteResponse)
def execute_endpoint(
    req: ExecuteRequest,
    current: CurrentUser = Depends(require_permission("uitest:trigger")),
) -> ExecuteResponse:
    """Execute a Playwright .spec.ts in headless Chromium and return the result."""
    return execute_spec(req)
