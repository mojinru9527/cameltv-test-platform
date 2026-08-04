"""Playground API — test case → Playwright spec compile + execute."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.models.test_case import TestCase
from app.schemas.playground import CompileRequest, CompileResponse, ExecuteRequest, ExecuteResponse
from app.services.playground_service import build_gherkin_from_case, compile_spec, execute_spec

router = APIRouter(prefix="/playground", tags=["Playground"])


@router.post("/compile", response_model=CompileResponse)
def compile_endpoint(
    req: CompileRequest,
    current: CurrentUser = Depends(require_permission("uitest:list")),
    db: Session = Depends(get_db),
) -> CompileResponse:
    """Compile a test case source (Gherkin/Markdown/plain) into a Playwright .spec.ts."""
    source = req.source
    if req.case_id:
        query = select(TestCase).where(
            TestCase.case_id == req.case_id,
            TestCase.is_deleted.is_(False),
        )
        if current.project_id:
            query = query.where(TestCase.project_id == current.project_id)
        case = db.scalar(query.limit(1))
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
