"""Playground API schemas — compile + execute test specs."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    gherkin = "gherkin"
    markdown = "markdown"
    plain = "plain"


class CompileRequest(BaseModel):
    source: str = Field(..., description="Test case source text (Gherkin/Markdown/plain)")
    source_type: SourceType = Field(default=SourceType.gherkin, description="Source format")
    case_id: Optional[str] = Field(
        default=None,
        description="功能用例编号（如 TC-LIVE-001）；提供时忽略 source，从用例 steps 编译",
    )


class CompileResponse(BaseModel):
    spec_code: str = Field(..., description="Generated .spec.ts Playwright code")
    spec_type: str = Field(default="playwright", description="Target framework")
    compile_ms: float = Field(default=0.0, description="Compilation time in ms")


class ExecuteRequest(BaseModel):
    spec_code: str = Field(..., description=".spec.ts code to execute")
    timeout_ms: int = Field(default=30000, ge=5000, le=120000, description="Execution timeout ms")


class ExecuteResponse(BaseModel):
    passed: bool = Field(..., description="Whether all tests passed")
    stdout: str = Field(default="", description="Execution stdout")
    stderr: str = Field(default="", description="Execution stderr")
    screenshot_base64: Optional[str] = Field(default=None, description="Screenshot as base64 PNG")
    duration_ms: float = Field(default=0.0, description="Execution duration in ms")


# ── Batch 166：功能用例批量编译 / 批量执行 ──

class PlaygroundBatchCompileRequest(BaseModel):
    case_ids: list[int] = Field(..., min_length=1, max_length=100)


class PlaygroundCaseCompileItem(BaseModel):
    case_id: int
    case_title: str = ""
    spec_code: str = ""
    has_todo: bool = False


class PlaygroundBatchCompileResponse(BaseModel):
    total: int = 0
    items: list[PlaygroundCaseCompileItem] = []


class PlaygroundBatchRunRequest(BaseModel):
    case_ids: list[int] = Field(..., min_length=1, max_length=50)
    write_back_to_ui: bool = True
    timeout_ms: int = Field(default=60000, ge=5000, le=180000)


class PlaygroundCaseRunResult(BaseModel):
    case_id: int
    case_title: str = ""
    spec_code: str = ""
    passed: bool = False
    stdout: str = ""
    stderr: str = ""
    screenshot_base64: Optional[str] = None
    duration_ms: float = 0.0
    ui_job_id: Optional[int] = None
    todo_blocked: bool = False


class PlaygroundBatchRunResponse(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    todo_blocked: int = 0
    results: list[PlaygroundCaseRunResult] = []
    report: dict = {}
