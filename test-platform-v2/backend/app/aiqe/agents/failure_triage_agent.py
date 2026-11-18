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
    recommended_experiment: Literal["E1", "E2", "E3", "E4", "E5", "E6"] | None = None
    confidence: None = None
    confidence_band: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"] | None = None
    status: Literal["PROPOSED"] = "PROPOSED"


class TriageResult(BaseModel):
    execution_outcome: Literal["FAIL", "INCOMPLETE", "ERROR", "UNKNOWN"] = "FAIL"
    attribution_status: Literal["NEEDS_EXPERIMENT", "UNKNOWN"] = "NEEDS_EXPERIMENT"
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    human_review_required: bool = True
    auto_close_defect: bool = False


def compute_confidence_band(
    *,
    supporting: list[str],
    contradicting: list[str],
    reproducible: bool = False,
) -> str:
    """确定性证据等级（v1.5 §04-5.2），**不接受模型自填置信度**。

    - HIGH：至少 1 条直接观测 + 1 条独立来源佐证 + 可重复；
    - MEDIUM：有直接信号但缺乏独立重复；
    - LOW：只有单一弱关联；
    - UNKNOWN：无足够数据。
    """
    unique_supporting = {str(item) for item in supporting if str(item).strip()}
    unique_contradicting = {str(item) for item in contradicting if str(item).strip()}
    if not unique_supporting:
        return "UNKNOWN"
    if len(unique_supporting) >= 1 and reproducible and unique_contradicting:
        return "HIGH"
    if len(unique_supporting) >= 2 and reproducible:
        return "HIGH"
    if len(unique_supporting) >= 1:
        return "MEDIUM"
    return "LOW"


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
        "一致性硬约束：若 attribution_status=UNKNOWN，hypotheses 必须至少包含一条 "
        "classification=UNKNOWN；若没有 UNKNOWN 假设，attribution_status 必须为 NEEDS_EXPERIMENT。"
    )

    def triage(self, failure_context: dict) -> dict:
        return self.run(str(failure_context))

    def validate(self, data: dict, *, evidence_resolver=None) -> dict:
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

        payload = result.model_dump()
        for index, hypothesis in enumerate(payload["hypotheses"]):
            if hypothesis["confidence"] is not None:
                raise AgentSchemaError("confidence 必须为 null（不让模型自填置信度）")
            if hypothesis["classification"] == "CROSS_FEATURE_DEFECT" and not (
                hypothesis["supporting_evidence"]
            ):
                raise AgentSchemaError("CROSS_FEATURE_DEFECT 必须有用户路径失败证据")
            if result.attribution_status != "UNKNOWN" and not hypothesis["missing_evidence"]:
                raise AgentSchemaError("证据不足时必须显式列出 missing_evidence")
            if (
                result.attribution_status != "UNKNOWN"
                and hypothesis["recommended_experiment"] is None
            ):
                raise AgentSchemaError("非 UNKNOWN 归因必须给出 E1–E6 实验建议")

            refs = list(hypothesis["supporting_evidence"]) + list(
                hypothesis["contradicting_evidence"]
            )
            if evidence_resolver is not None:
                # AUD-016：所有 evidence refs 必须由服务端解析（存在 + 同项目 + 同 Run）。
                evidence_resolver(refs)
            hypothesis["confidence_band"] = compute_confidence_band(
                supporting=list(hypothesis["supporting_evidence"]),
                contradicting=list(hypothesis["contradicting_evidence"]),
                reproducible=hypothesis["recommended_experiment"] == "E1",
            )
            payload["hypotheses"][index] = hypothesis

        return payload
