"""P2 / AUD-013：MCP HTTP adapter（规范工具名 → 同一套 FastAPI Service）。

约束（v1.5 §03 追加）：

- 每个 MCP Tool 必须映射到**同一个** FastAPI Service，不允许 MCP Server 自行直连 DB/Runner；
- 写/执行/审批类工具必须携带审批 token（由 gateway 校验后再透传）；
- 调用必须可审计：记录 actor/client/tool/参数 hash/结果引用/correlation id，并脱敏参数。
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HttpMcpAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    scope: str


#: 规范工具名 → REST 路由（与 /api/v1/aiqe 合同一致）。
TOOL_ROUTES: dict[str, Route] = {
    "aiqe.project.get_context": Route("GET", "/api/v1/aiqe/runs", "READ"),
    "aiqe.requirement.analyze": Route("POST", "/api/v1/aiqe/contracts", "WRITE_DRAFT"),
    "aiqe.requirement.get": Route("GET", "/api/v1/aiqe/contracts/{contract_id}", "READ"),
    "aiqe.testcase.generate": Route("POST", "/api/v1/aiqe/cases", "WRITE_DRAFT"),
    "aiqe.testcase.review": Route(
        "POST", "/api/v1/aiqe/cases/{case_id}/review", "APPROVE"
    ),
    "aiqe.workflow.plan": Route("POST", "/api/v1/aiqe/agent-tasks", "WRITE_DRAFT"),
    "aiqe.run.get": Route("GET", "/api/v1/aiqe/runs/{run_id}", "READ"),
    "aiqe.run.events": Route("GET", "/api/v1/aiqe/runs/{run_id}/events", "READ"),
    "aiqe.triage.analyze": Route(
        "POST", "/api/v1/aiqe/runs/{run_id}/observations", "WRITE_DRAFT"
    ),
    "aiqe.regression.plan": Route("POST", "/api/v1/aiqe/impact/plan", "WRITE_DRAFT"),
    "aiqe.regression.launch": Route(
        "POST", "/api/v1/aiqe/defects/{defect_id}/regressions", "EXECUTE_TEST"
    ),
    "aiqe.learning.review": Route(
        "POST", "/api/v1/aiqe/learning/candidates/{candidate_id}/approve", "APPROVE"
    ),
    "aiqe.learning.activate": Route(
        "POST", "/api/v1/aiqe/learning/candidates/{candidate_id}/activate", "APPROVE"
    ),
}
#: 规范工具名 → 参数路径键（从 arguments 提取并填充 path 模板）。
PATH_PARAMS: dict[str, str] = {
    "aiqe.requirement.get": "contract_id",
    "aiqe.testcase.review": "case_id",
    "aiqe.run.get": "run_id",
    "aiqe.run.events": "run_id",
    "aiqe.triage.analyze": "run_id",
    "aiqe.regression.launch": "defect_id",
    "aiqe.learning.review": "candidate_id",
    "aiqe.learning.activate": "candidate_id",
}
READ_SCOPES = frozenset({"READ", "PROD_READONLY"})
#: 尚无 REST 入口的规范工具：显式报错而不是静默映射到不存在的接口。
UNSUPPORTED_TOOLS: frozenset[str] = frozenset({"aiqe.run.launch", "aiqe.benchmark.run"})


def _args_hash(arguments: dict[str, Any]) -> str:
    payload = json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()[:16]


class HttpMcpAdapter:
    def __init__(
        self,
        base_url: str,
        token: str = "",
        *,
        client: httpx.Client | None = None,
        project_id: int | None = None,
        correlation_id: str = "",
        actor: str = "mcp-client",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = client or httpx.Client(timeout=15)
        self.project_id = project_id
        self.correlation_id = correlation_id
        self.actor = actor

    def _headers(self, approval_token: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"X-Client": self.actor}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.project_id is not None:
            headers["X-Project-Id"] = str(self.project_id)
        if self.correlation_id:
            headers["X-Correlation-Id"] = self.correlation_id
        if approval_token:
            headers["X-Approval-Token"] = approval_token
        return headers

    def _dispatch(
        self,
        tool: str,
        arguments: dict[str, Any],
        *,
        approval_token: str | None = None,
    ) -> Any:
        if tool in UNSUPPORTED_TOOLS:
            raise HttpMcpAdapterError(f"工具尚未暴露 REST 入口: {tool}")
        route = TOOL_ROUTES.get(tool)
        if route is None:
            raise HttpMcpAdapterError(f"未知工具: {tool}")
        payload = dict(arguments or {})
        path = route.path
        param_key = PATH_PARAMS.get(tool)
        if param_key:
            value = payload.pop(param_key, None)
            if not value:
                raise HttpMcpAdapterError(f"{tool} 缺少参数 {param_key}")
            path = path.replace("{" + param_key + "}", str(value))
        if route.scope not in READ_SCOPES and not approval_token:
            raise HttpMcpAdapterError(f"{tool} 需要审批 token")
        logger.info(
            "aiqe.mcp.tool_call",
            extra={
                "actor": self.actor,
                "tool": tool,
                "scope": route.scope,
                "args_hash": _args_hash(arguments or {}),
                "correlation_id": self.correlation_id,
            },
        )
        request_kwargs: dict[str, Any] = {"headers": self._headers(approval_token)}
        if route.method == "GET":
            request_kwargs["params"] = payload
        else:
            request_kwargs["json"] = payload
        response = self.client.request(
            route.method, f"{self.base_url}{path}", **request_kwargs
        )
        if response.status_code >= 400:
            raise HttpMcpAdapterError(f"HTTP {response.status_code}: {response.text[:200]}")
        try:
            body = response.json()
        except ValueError:  # pragma: no cover - 非 JSON 响应
            return {"raw": response.text[:2000]}
        # 统一去掉 {code,msg,data} envelope 的壳，交给 MCP 层输出 data。
        if isinstance(body, dict) and {"code", "data"} <= set(body):
            return body.get("data")
        return body

    def reader(self, tool: str, arguments: dict[str, Any]) -> Any:
        scope = TOOL_ROUTES.get(tool, Route("", "", "WRITE"))
        if tool not in TOOL_ROUTES or scope.scope not in READ_SCOPES:
            raise HttpMcpAdapterError(f"非只读工具不能走 reader: {tool}")
        return self._dispatch(tool, arguments)

    def writer(self, tool: str, arguments: dict[str, Any], approval_token: str) -> Any:
        scope = TOOL_ROUTES.get(tool, Route("", "", "WRITE"))
        if tool not in TOOL_ROUTES or scope.scope in READ_SCOPES:
            raise HttpMcpAdapterError(f"只读工具不能走 writer: {tool}")
        return self._dispatch(tool, arguments, approval_token=approval_token)
