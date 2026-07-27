"""拉取 OpenAPI 3.x spec（JSON/YAML）→ 结构化 EndpointSpec 列表。

支持远程 URL、本地文件路径。处理 $ref 引用展开。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml


@dataclass
class EndpointSpec:
    """单个接口的结构化描述。"""
    method: str
    path: str
    summary: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body: dict[str, Any] | None = None
    responses: dict[str, Any] = field(default_factory=dict)
    security: list[dict[str, Any]] | None = None
    # 来源标记
    source: str = ""  # "swagger" | "ui-capture"


class SwaggerParser:
    """解析 OpenAPI 3.x spec，输出 EndpointSpec 列表。"""

    def __init__(self):
        self._refs: dict[str, Any] = {}
        self._spec: dict[str, Any] = {}

    def parse(self, source: str) -> list[EndpointSpec]:
        """主入口：从 URL 或本地文件读取并解析。"""
        self._spec = self._load(source)
        self._refs = {}
        return self._extract_endpoints()

    def _load(self, source: str) -> dict[str, Any]:
        """加载 spec（HTTP 远程 或 本地文件）。"""
        if urlparse(source).scheme in ("http", "https"):
            resp = httpx.get(source, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            content = resp.text
            # 尝试从 content-type 判断
            ct = resp.headers.get("content-type", "")
            if "yaml" in ct or source.endswith((".yaml", ".yml")):
                return yaml.safe_load(content) or {}
            return resp.json()
        else:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Spec 文件不存在: {source}")
            content = path.read_text(encoding="utf-8")
            if path.suffix in (".yaml", ".yml"):
                return yaml.safe_load(content) or {}
            return json.loads(content)

    def _resolve_ref(self, ref: str) -> Any:
        """解析 $ref 引用。"""
        if ref in self._refs:
            return self._refs[ref]

        parts = ref.lstrip("#/").split("/")
        current = self._spec
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        self._refs[ref] = current
        return current

    def _extract_endpoints(self) -> list[EndpointSpec]:
        """从 spec['paths'] 提取所有接口。"""
        paths = self._spec.get("paths", {})
        endpoints: list[EndpointSpec] = []

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, detail in methods.items():
                if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    continue
                if not isinstance(detail, dict):
                    continue

                # 解析 parameters（合并 path-level 和 method-level）
                params = list(paths[path].get("parameters", []) or [])
                params.extend(detail.get("parameters", []) or [])

                # 展开 $ref
                resolved_params = []
                for p in params:
                    if "$ref" in p:
                        resolved = self._resolve_ref(p["$ref"])
                        if resolved:
                            resolved_params.append(resolved)
                    else:
                        resolved_params.append(p)

                # 展开 requestBody $ref
                req_body = detail.get("requestBody")
                if req_body and "$ref" in req_body:
                    req_body = self._resolve_ref(req_body["$ref"])

                endpoints.append(EndpointSpec(
                    method=method.upper(),
                    path=path,
                    summary=detail.get("summary", ""),
                    description=detail.get("description", ""),
                    tags=detail.get("tags", []),
                    parameters=resolved_params,
                    request_body=req_body,
                    responses=detail.get("responses", {}),
                    security=detail.get("security"),
                    source="swagger",
                ))

        return endpoints
