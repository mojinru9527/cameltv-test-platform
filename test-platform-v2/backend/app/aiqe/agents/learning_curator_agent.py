"""AUD-013：A6 Learning Curator Agent（从已确认缺陷生成规则候选）。

约束（v1.5 §03 AUD-013 / AUD-018）：

- 只能产出 **Learning Candidate Draft**，必须经 Benchmark + 人工批准才能激活；
- 每条候选必须引用真实缺陷/来源（``source_refs`` 非空且可解析）；
- Agent 不得自动激活规则、不得修改已生效规则。
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError
from app.aiqe.agents.protocol import AgentContext, AgentResult, stable_hash

AGENT_VERSION = "1.1.0"
SYSTEM_PROMPT = (
    "你是 BugPattern Curator。基于已确认缺陷与证据，提出可复用的规则候选。"
    "只输出 JSON：{pattern_key, description, conditions[], source_refs[], "
    "false_positive_risk, rationale}。source_refs 必须来自输入，不得编造。"
)


class LearningCandidateProposal(BaseModel):
    pattern_key: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    conditions: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(min_length=1)
    false_positive_risk: str = Field(default="UNKNOWN", max_length=32)
    rationale: str = Field(default="", max_length=2000)


class LearningCuratorAgent:
    key = "A6"
    version = AGENT_VERSION
    model = "deepseek-chat"
    system_prompt = SYSTEM_PROMPT

    def __init__(self, llm: Callable[[str, str], str] | None = None, *, model: str | None = None) -> None:
        self._llm = llm
        if model:
            self.model = model

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            proposal = LearningCandidateProposal.model_validate(data)
        except ValidationError as exc:
            raise AgentSchemaError(f"Learning Candidate schema 校验失败: {exc}") from exc
        if not proposal.source_refs:
            raise AgentSchemaError("Learning Candidate 必须引用真实缺陷/来源")
        return {
            "candidate": proposal.model_dump(),
            "activation": "REQUIRES_BENCHMARK_AND_HUMAN_APPROVAL",
            "auto_activated": False,
        }

    def execute(self, context: AgentContext, request: str) -> AgentResult:
        input_hash = stable_hash(request)
        if self._llm is None:
            return AgentResult(
                agent_key=self.key,
                agent_version=self.version,
                status="FAILED",
                model_name=self.model,
                prompt_version=stable_hash(self.system_prompt),
                input_hash=input_hash,
                error_code="MODEL_UNAVAILABLE",
                warnings=["LLM 客户端不可用（Key 缺失或未注入）"],
            )
        # V16-019：A6 也通过 ToolExecutor 取证（缺陷/数据集事实），与 A1–A5 一致。
        prompt = request
        executor = getattr(context, "tool_executor", None)
        if executor is not None:
            tool_evidence = {"defects": executor.safe_call("read_defects")}
            prompt = (
                f"{request}\n\n[TOOL_EVIDENCE]\n"
                + json.dumps(tool_evidence, ensure_ascii=False, default=str)[:4000]
            )
        raw = self._llm(self.system_prompt, prompt)
        try:
            text = str(raw or "").strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:]
            output = self.validate(json.loads(text))
        except AgentSchemaError as exc:
            return AgentResult(
                agent_key=self.key,
                agent_version=self.version,
                status="FAILED",
                model_name=self.model,
                prompt_version=stable_hash(self.system_prompt),
                input_hash=input_hash,
                error_code="SCHEMA_INVALID",
                warnings=[str(exc)],
            )
        except (ValueError, TypeError) as exc:
            return AgentResult(
                agent_key=self.key,
                agent_version=self.version,
                status="FAILED",
                model_name=self.model,
                prompt_version=stable_hash(self.system_prompt),
                input_hash=input_hash,
                error_code="INVALID_JSON",
                warnings=[str(exc)],
            )
        refs: list[Any] = []
        if context.evidence_resolver is not None:
            refs = context.evidence_resolver(output["candidate"]["source_refs"])
        return AgentResult(
            agent_key=self.key,
            agent_version=self.version,
            status="COMPLETED" if refs else "PARTIAL",
            output=output,
            source_refs=[str(item) for item in output["candidate"]["source_refs"]],
            tool_calls=list(executor.tool_calls()) if executor is not None else [],
            model_name=self.model,
            prompt_version=stable_hash(self.system_prompt),
            input_hash=input_hash,
            output_hash=stable_hash(output),
            warnings=[] if refs else ["EVIDENCE_NOT_RESOLVED"],
            needs_human=not refs,
        )


__all__ = ["AGENT_VERSION", "SYSTEM_PROMPT", "LearningCandidateProposal", "LearningCuratorAgent"]
