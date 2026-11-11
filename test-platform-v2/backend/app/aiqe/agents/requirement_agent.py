"""M3 / TA-019：A0 Requirement Agent（需求 → 验收标准，必须带来源引用）。"""
from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError, BaseAgent


class AcceptanceCriterion(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_ref: str = Field(min_length=1, description="需求原文引用/章节")


class RequirementAssessment(BaseModel):
    summary: str = Field(min_length=1)
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)


class RequirementAgent(BaseAgent):
    key = "A0"
    model = "deepseek-chat"
    system_prompt = (
        "你是需求评估 Agent。输出严格 JSON："
        '{"summary": str, "acceptance_criteria": [{"id": str, "text": str, "source_ref": str}], '
        '"risks": [str]}。每条验收标准必须给出 source_ref（需求原文片段/章节），不得编造。'
    )

    def validate(self, data: dict) -> dict:
        try:
            parsed = RequirementAssessment.model_validate(data)
        except ValidationError as exc:
            raise AgentSchemaError(f"需求评估 schema 校验失败: {exc}") from exc
        if any(not criterion.source_ref.strip() for criterion in parsed.acceptance_criteria):
            raise AgentSchemaError("每条验收标准都必须带 source_ref")
        return parsed.model_dump()
