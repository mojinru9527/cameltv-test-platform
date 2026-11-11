"""M3 / TA-019：Agent 基类（schema 严格校验 + Key 缺失 fail-closed）。"""
from __future__ import annotations

import json
from collections.abc import Callable


class AgentUnavailable(RuntimeError):
    """模型 Key/客户端不可用；必须 fail-closed，禁止静默降级。"""


class AgentSchemaError(ValueError):
    """模型输出不符合约定 schema。"""


class BaseAgent:
    key = "base"
    model = "deepseek-chat"
    system_prompt = ""

    def __init__(
        self,
        llm: Callable[[str, str], str] | None,
        *,
        model: str | None = None,
    ) -> None:
        self._llm = llm
        if model:
            self.model = model

    def _call(self, input_text: str) -> str:
        if self._llm is None:
            raise AgentUnavailable("LLM 客户端不可用（Key 缺失或未注入）")
        return self._llm(self.system_prompt, input_text)

    @staticmethod
    def parse_json(raw: str) -> dict:
        if not isinstance(raw, str) or not raw.strip():
            raise AgentSchemaError("模型返回为空")
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AgentSchemaError(f"模型输出不是合法 JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise AgentSchemaError("模型输出必须是 JSON 对象")
        return data

    def validate(self, data: dict) -> dict:
        raise NotImplementedError

    def run(self, input_text: str) -> dict:
        return self.validate(self.parse_json(self._call(input_text)))
