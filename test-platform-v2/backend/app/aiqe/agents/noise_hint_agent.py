"""M3 / TA-024.2：Noise Hint Agent（13 号 §10.4 Skill）。

对失败证据给出 1-3 条**疑似噪音** hint + 证据引用；不替人判断、不自动关缺陷。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError, BaseAgent

FACTORS = (
    "AD_JITTER",
    "FEATURE_FLAG",
    "CONCURRENT_RUN",
    "ENV_DRIFT",
    "DATA_LEAK",
    "UNKNOWN",
)
EVIDENCE_PREFIXES = ("artifact:", "event:", "flag:", "run:", "signal:")
Factor = Literal[
    "AD_JITTER", "FEATURE_FLAG", "CONCURRENT_RUN", "ENV_DRIFT", "DATA_LEAK", "UNKNOWN"
]


class NoiseHint(BaseModel):
    hint: str = Field(min_length=1)
    suspected_factor: Factor
    evidence_refs: list[str] = Field(min_length=1)


class NoiseHintResult(BaseModel):
    hints: list[NoiseHint] = Field(min_length=1, max_length=3)
    human_review_required: bool = True
    auto_close_defect: bool = False


class NoiseHintAgent(BaseAgent):
    key = "NOISE_HINT"
    model = "deepseek-chat"
    system_prompt = (
        "你是噪音归因 hint Agent。输出严格 JSON："
        '{"hints":[{"hint":str,"suspected_factor":"AD_JITTER|FEATURE_FLAG|CONCURRENT_RUN|'
        'ENV_DRIFT|DATA_LEAK|UNKNOWN","evidence_refs":["artifact:…","event:…"]}],'
        '"human_review_required":true,"auto_close_defect":false}。'
        "最多 3 条 hint；每条必须引用证据；不替人判断、不得自动关闭缺陷。"
    )

    def analyze(self, failure_context: dict) -> dict:
        return self.run(str(failure_context))

    def validate(self, data: dict) -> dict:
        try:
            result = NoiseHintResult.model_validate(data)
        except ValidationError as exc:
            raise AgentSchemaError(f"噪音 hint schema 校验失败: {exc}") from exc

        if result.auto_close_defect:
            raise AgentSchemaError("噪音 hint 不得自动关闭缺陷")
        if not result.human_review_required:
            raise AgentSchemaError("噪音 hint 必须 human_review_required=true")

        for hint in result.hints:
            if not hint.evidence_refs:
                raise AgentSchemaError(f"hint 必须引用证据: {hint.hint}")
            for ref in hint.evidence_refs:
                if not any(str(ref).startswith(prefix) for prefix in EVIDENCE_PREFIXES):
                    raise AgentSchemaError(f"非法证据引用（需 artifact:/event:/flag:/run:/signal:）: {ref}")
        return result.model_dump()
