"""M3 / TA-019：Agent 基类（schema 严格校验 + Key 缺失 fail-closed）。"""
from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from typing import Any


class AgentUnavailable(RuntimeError):
    """模型 Key/客户端不可用；必须 fail-closed，禁止静默降级。"""


class AgentSchemaError(ValueError):
    """模型输出不符合约定 schema。"""

    code = "SCHEMA_INVALID"


class AgentEvidenceError(AgentSchemaError):
    """V16-012：证据 resolver 缺失/无效/跨项目 → 输出不可采信。"""

    code = "INVALID_EVIDENCE"

    def __init__(self, message: str, *, reason: str = "INVALID_EVIDENCE") -> None:
        super().__init__(message)
        self.reason = reason


class BaseAgent:
    key = "base"
    model = "deepseek-chat"
    system_prompt = ""
    #: 工具证据注入提示词的上限，避免超长上下文与 Secret 泄漏。
    tool_evidence_limit = 4000

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

    def gather_tool_evidence(self, executor: Any) -> dict[str, Any]:
        """V16-019：Agent 通过 ToolExecutor 取证。

        默认不调用任何工具；子类声明自己需要的只读工具。工具失败不抛出，
        以 ``{"ok": false, "error": ...}`` 进入提示词，避免 Agent 在缺证据时
        假装有结论。
        """
        return {}

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

    def run(self, input_text: str, *, context: Any = None) -> dict:
        """V16-012/019：透传 evidence_resolver 与工具执行器。

        - ``context.tool_executor`` 存在时，先按 Agent 声明的只读工具取证，
          把证据注入提示词（LLM 看到的是真实 DB/仓库事实）；
        - ``context.evidence_resolver`` 仅在 validate 显式声明时传入。
        """
        executor = getattr(context, "tool_executor", None) if context is not None else None
        tool_evidence: dict[str, Any] = {}
        if executor is not None:
            tool_evidence = self.gather_tool_evidence(executor)
        prompt = input_text
        if tool_evidence:
            serialized = json.dumps(tool_evidence, ensure_ascii=False, default=str)
            prompt = (
                f"{input_text}\n\n[TOOL_EVIDENCE]\n{serialized[: self.tool_evidence_limit]}"
            )
        data = self.parse_json(self._call(prompt))
        resolver = getattr(context, "evidence_resolver", None) if context is not None else None
        params = inspect.signature(self.validate).parameters
        if "evidence_resolver" in params:
            return self.validate(data, evidence_resolver=resolver)  # type: ignore[call-arg]
        return self.validate(data)


__all__ = [
    "AgentEvidenceError",
    "AgentSchemaError",
    "AgentUnavailable",
    "BaseAgent",
]
