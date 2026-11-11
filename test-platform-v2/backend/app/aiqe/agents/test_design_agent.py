"""M3 / TA-020：A2 Test Design / Review Agent（13 号 §19 TA-020）。

规则：
- 每条 P0 用例必须带 `acceptance_refs`（验收断言引用），否则不得批准；
- 旧用例覆盖充分（`coverage_sufficient=True`）时只允许 `decision="skip"`，不得重复新增；
- `reject` 必须给出 `reject_reason`；`skip` 必须给出 `coverage_notes`；
- 输出严格 Pydantic 校验，非法 schema 一律拒绝。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError, BaseAgent


class DesignCase(BaseModel):
    title: str = Field(min_length=1)
    priority: Literal["P0", "P1", "P2", "P3"]
    steps: list[str] = Field(min_length=1)
    acceptance_refs: list[str] = Field(default_factory=list)


class DesignResult(BaseModel):
    decision: Literal["approve", "reject", "skip"]
    cases: list[DesignCase] = Field(default_factory=list)
    coverage_notes: str = ""
    reject_reason: str = ""
    duplicate_of: list[str] = Field(default_factory=list)


class TestDesignAgent(BaseAgent):
    key = "A2"
    model = "deepseek-chat"
    system_prompt = (
        "你是测试设计/评审 Agent。输出严格 JSON："
        '{"decision":"approve|reject|skip","cases":[{"title","priority":"P0|P1|P2|P3",'
        '"steps":[...],"acceptance_refs":[...]}],"coverage_notes","reject_reason"}。'
        "规则：P0 用例必须带 acceptance_refs；已有用例覆盖充分时输出 skip 且 cases 为空，"
        "不得重复新增；reject 必须说明原因。"
    )

    def __init__(self, llm, *, model: str | None = None) -> None:
        super().__init__(llm, model=model)
        self._coverage_sufficient = False

    def run_design(
        self,
        assessment: dict,
        existing_cases: list[dict] | None = None,
        *,
        coverage_sufficient: bool = False,
    ) -> dict:
        self._coverage_sufficient = coverage_sufficient
        payload = (
            "需求评估:\n"
            + str(assessment)
            + "\n已有用例:\n"
            + str(existing_cases or [])
            + f"\n覆盖充分: {coverage_sufficient}"
        )
        return self.run(payload)

    def validate(self, data: dict) -> dict:
        try:
            result = DesignResult.model_validate(data)
        except ValidationError as exc:
            raise AgentSchemaError(f"测试设计 schema 校验失败: {exc}") from exc

        if result.decision == "approve":
            if not result.cases:
                raise AgentSchemaError("approve 必须至少包含 1 条用例")
            if self._coverage_sufficient:
                raise AgentSchemaError("旧用例已覆盖充分，不得重复新增用例（应输出 skip）")
            for case in result.cases:
                if case.priority == "P0" and not [
                    ref for ref in case.acceptance_refs if ref.strip()
                ]:
                    raise AgentSchemaError(f"P0 用例必须带验收断言引用: {case.title}")
        elif result.decision == "skip":
            if result.cases:
                raise AgentSchemaError("skip 时 cases 必须为空")
            if not result.coverage_notes.strip():
                raise AgentSchemaError("skip 必须说明 coverage_notes")
        else:  # reject
            if not result.reject_reason.strip():
                raise AgentSchemaError("reject 必须说明 reject_reason")
            if result.cases:
                raise AgentSchemaError("reject 时不得输出 cases")

        return result.model_dump()
