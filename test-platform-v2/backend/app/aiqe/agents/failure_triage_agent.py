"""M3 / TA-024：A4 Failure & Triage Agent（13 号 §11.7 / §11.8）。

安全规则（fail-closed）：
- 归因只输出 draft：`humane_review_required=True`，**不得自动关闭缺陷**；
- `confidence` 必须为 null（不让模型自填百分比）；
- 证据不足/无法归因 → `UNKNOWN`（不允许编造根因）；
- `CROSS_FEATURE_DEFECT` 必须有实际用户路径失败证据。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError, BaseAgent

CLASSIFICATIONS = (
    "PRODUCT_DEFECT",
    "CROSS_FEATURE_DEFECT",
    "ENVIRONMENT",
    "TEST_DATA",
    "CONCURRENCY",
    "THIRD_PARTY",
    "NETWORK",
    "TIME",
    "AUTOMATION",
    "REQUIREMENT_GAP",
    "FLAKY",
    "UNKNOWN",
)
Classification = Literal[
    "PRODUCT_DEFECT",
    "CROSS_FEATURE_DEFECT",
    "ENVIRONMENT",
    "TEST_DATA",
    "CONCURRENCY",
    "THIRD_PARTY",
    "NETWORK",
    "TIME",
    "AUTOMATION",
    "REQUIREMENT_GAP",
    "FLAKY",
    "UNKNOWN",
]


class Hypothesis(BaseModel):
    classification: Classification
    summary: str = Field(min_length=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence: None = None
    status: Literal["PROPOSED"] = "PROPOSED"


class TriageResult(BaseModel):
    execution_outcome: Literal["FAIL", "INCOMPLETE", "ERROR", "UNKNOWN"] = "FAIL"
    attribution_status: Literal["NEEDS_EXPERIMENT", "UNKNOWN"] = "NEEDS_EXPERIMENT"
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    human_review_required: bool = True
    auto_close_defect: bool = False


class FailureTriageAgent(BaseAgent):
    key = "A4"
    model = "deepseek-chat"
    system_prompt = (
        "你是失败归因 Agent。输出严格 JSON："
        '{"execution_outcome":"FAIL|INCOMPLETE|ERROR|UNKNOWN",'
        '"attribution_status":"NEEDS_EXPERIMENT|UNKNOWN",'
        '"hypotheses":[{"classification":"PRODUCT_DEFECT|CROSS_FEATURE_DEFECT|ENVIRONMENT|'
        'TEST_DATA|CONCURRENCY|THIRD_PARTY|NETWORK|TIME|AUTOMATION|REQUIREMENT_GAP|FLAKY|UNKNOWN",'
        '"summary":str,"supporting_evidence":[str],"contradicting_evidence":[str],'
        '"missing_evidence":[str]}],"human_review_required":true,"auto_close_defect":false}。'
        "confidence 必须为 null；证据不足输出 UNKNOWN；不得自动关闭缺陷。"
    )

    def triage(self, failure_context: dict) -> dict:
        return self.run(str(failure_context))

    def validate(self, data: dict) -> dict:
        try:
            result = TriageResult.model_validate(data)
        except ValidationError as exc:
            raise AgentSchemaError(f"归因 schema 校验失败: {exc}") from exc

        if result.auto_close_defect:
            raise AgentSchemaError("AI 不得自动关闭缺陷/归为非缺陷")
        if not result.human_review_required:
            raise AgentSchemaError("归因结果必须 human_review_required=true")
        if not result.hypotheses:
            raise AgentSchemaError("至少需要 1 条归因假设（无法归因时输出 UNKNOWN）")

        unknown = [h for h in result.hypotheses if h.classification == "UNKNOWN"]
        if unknown and result.attribution_status != "UNKNOWN":
            raise AgentSchemaError("UNKNOWN 归因时 attribution_status 必须为 UNKNOWN")
        if result.attribution_status == "UNKNOWN" and not unknown:
            raise AgentSchemaError("attribution_status=UNKNOWN 时必须包含 UNKNOWN 假设")

        for hypothesis in result.hypotheses:
            if hypothesis.confidence is not None:
                raise AgentSchemaError("confidence 必须为 null（不让模型自填置信度）")
            if hypothesis.classification == "CROSS_FEATURE_DEFECT" and not (
                hypothesis.supporting_evidence
            ):
                raise AgentSchemaError("CROSS_FEATURE_DEFECT 必须有用户路径失败证据")

        return result.model_dump()
