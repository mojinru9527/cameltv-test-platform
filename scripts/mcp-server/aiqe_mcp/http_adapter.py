"""P2：MCP HTTP adapter（生产 reader/writer，替换 stdio 占位）。"""
from __future__ import annotations

from typing import Any

import httpx


class HttpMcpAdapterError(RuntimeError):
    pass


class HttpMcpAdapter:
    def __init__(self, base_url: str, token: str = "", *, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = client or httpx.Client(timeout=15)

    def _headers(self, approval_token: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if approval_token:
            headers["X-Approval-Token"] = approval_token
        return headers

    def reader(self, tool: str, arguments: dict[str, Any]) -> Any:
        run_id = str(arguments.get("run_id") or "")
        if tool == "list_runs":
            response = self.client.get(f"{self.base_url}/api/v1/aiqe/runs", params=arguments, headers=self._headers())
        elif tool == "get_run" and run_id:
            response = self.client.get(f"{self.base_url}/api/v1/aiqe/runs/{run_id}", headers=self._headers())
        else:
            raise HttpMcpAdapterError(f"未知只读工具: {tool}")
        if response.status_code >= 400:
            raise HttpMcpAdapterError(f"HTTP {response.status_code}: {response.text[:200]}")
        return response.json()

    def writer(self, tool: str, arguments: dict[str, Any], approval_token: str) -> Any:
        run_id = str(arguments.get("run_id") or "")
        if tool == "create_run":
            response = self.client.post(
                f"{self.base_url}/api/v1/aiqe/runs",
                json=arguments,
                headers=self._headers(approval_token),
            )
        elif tool == "retry_run" and run_id:
            response = self.client.post(
                f"{self.base_url}/api/v1/aiqe/runs/{run_id}/retry",
                json=arguments,
                headers=self._headers(approval_token),
            )
        else:
            raise HttpMcpAdapterError(f"未知写工具: {tool}")
        if response.status_code >= 400:
            raise HttpMcpAdapterError(f"HTTP {response.status_code}: {response.text[:200]}")
        return response.json()
