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
