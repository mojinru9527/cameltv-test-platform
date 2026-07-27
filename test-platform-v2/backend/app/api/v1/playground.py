"""Playground API — test case → Playwright spec compile + execute."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.playground import CompileRequest, CompileResponse, ExecuteRequest, ExecuteResponse
from app.services.playground_service import compile_spec, execute_spec

router = APIRouter(prefix="/playground", tags=["Playground"])


@router.post("/compile", response_model=CompileResponse)
def compile_endpoint(req: CompileRequest) -> CompileResponse:
    """Compile a test case source (Gherkin/Markdown/plain) into a Playwright .spec.ts."""
    return compile_spec(req)


@router.post("/execute", response_model=ExecuteResponse)
def execute_endpoint(req: ExecuteRequest) -> ExecuteResponse:
    """Execute a Playwright .spec.ts in headless Chromium and return the result."""
    return execute_spec(req)
