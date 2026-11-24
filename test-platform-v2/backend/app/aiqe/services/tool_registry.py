"""V16-019：Tool Registry 真实绑定 / 权限 / schema / 审批 / 审计。

- 每个工具登记实现引用、输入/输出 schema、权限 scope、Project scope、副作用等级、
  幂等、超时、限流、是否需要人工审批、Secret 访问策略；
- allowlist 中缺失实现的工具标 UNAVAILABLE，Agent Plan 不得当可用；
- 参数 schema 校验（additionalProperties=false），拒绝隐式扩权；
- 每次调用写 ToolExecutionAudit（成功/拒绝都写），结果只保留摘要；
- 生产环境默认只允许 READ；WRITE/EXTERNAL 需要审批 token。
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any

import jsonschema
from sqlalchemy.orm import Session

from app.aiqe.agents.protocol import ToolNotAllowed, ToolRegistry
from app.aiqe.agents.registry import DEFAULT_TOOL_ALLOWLIST
from app.aiqe.models.tool import ToolExecutionAudit
from app.aiqe.services import tool_impls
from app.core.config import settings

READ = "READ"
WRITE = "WRITE"
EXTERNAL = "EXTERNAL"


class ToolUnavailable(PermissionError):
    code = "TOOL_UNAVAILABLE"


class ToolSchemaError(ValueError):
    code = "TOOL_SCHEMA_INVALID"


class ToolPermissionError(PermissionError):
    code = "TOOL_PERMISSION_DENIED"


class ToolRateLimited(PermissionError):
    code = "TOOL_RATE_LIMITED"


class ToolApprovalRequired(PermissionError):
    code = "TOOL_APPROVAL_REQUIRED"


class ToolTimeout(RuntimeError):
    code = "TOOL_TIMEOUT"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str = "1.0.0"
    implementation_ref: str = ""
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    permission_scope: str = "read"
    project_scope: str = "current_project"
    side_effect_level: str = READ
    idempotent: bool = True
    timeout_seconds: float = 10.0
    rate_limit_per_minute: int = 60
    requires_human_approval: bool = False
    secret_access_policy: str = "none"
    handler: Callable[..., Any] | None = None

    @property
    def available(self) -> bool:
        return self.handler is not None

    def validate(self) -> None:
        if not self.name:
            raise ToolSchemaError("tool name 不能为空")
        if self.side_effect_level not in {READ, WRITE, EXTERNAL}:
            raise ToolSchemaError(f"非法副作用等级: {self.side_effect_level}")
        if self.project_scope != "current_project":
            raise ToolSchemaError("project_scope 必须是 current_project")
        if self.secret_access_policy not in {"none", "handle_only"}:
            raise ToolSchemaError("secret_access_policy 只能是 none/handle_only")
        if not isinstance(self.input_schema, Mapping):
            raise ToolSchemaError("input_schema 必须是 object")
        if self.requires_human_approval and self.side_effect_level == READ:
            raise ToolSchemaError("READ 工具不应要求人工审批")


TOOL_INPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "read_project_context": {"type": "object", "properties": {}, "additionalProperties": False},
    "read_openapi": {"type": "object", "properties": {}, "additionalProperties": False},
    "read_run_evidence": {
        "type": "object",
        "properties": {"run_id": {"type": "string", "minLength": 1}},
        "required": ["run_id"],
        "additionalProperties": False,
    },
    "read_defects": {
        "type": "object",
        "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
        "additionalProperties": False,
    },
    "read_noise_rules": {
        "type": "object",
        "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}},
        "additionalProperties": False,
    },
    "read_benchmark_dataset": {
        "type": "object",
        "properties": {"dataset_id": {"type": "string", "minLength": 1}},
        "required": ["dataset_id"],
        "additionalProperties": False,
    },
    "read_requirements": {
        "type": "object",
        "properties": {
            "requirement_id": {"type": "string", "maxLength": 160},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "additionalProperties": False,
    },
    "read_git_diff": {
        "type": "object",
        "properties": {
            "base_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "head_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "max_files": {"type": "integer", "minimum": 1, "maximum": 500},
        },
        "required": ["base_sha", "head_sha"],
        "additionalProperties": False,
    },
}


def default_specs() -> dict[str, ToolSpec]:
    specs: dict[str, ToolSpec] = {}
    for name, handler in tool_impls.READ_TOOLS.items():
        specs[name] = ToolSpec(
            name=name,
            implementation_ref=f"app.aiqe.services.tool_impls.{handler.__name__}",
            input_schema=TOOL_INPUT_SCHEMAS.get(
                name, {"type": "object", "properties": {}, "additionalProperties": False}
            ),
            handler=handler,
        )
    # 写/外部工具：没有真实实现 → UNAVAILABLE（避免 allowlist 名称即可用）。
    for name in tool_impls.UNAVAILABLE_TOOLS:
        specs[name] = ToolSpec(
            name=name,
            implementation_ref="",
            side_effect_level=WRITE if name.startswith("create_") else READ,
            requires_human_approval=name.startswith("create_"),
        )
    return specs


def validate_implementations(
    specs: Mapping[str, ToolSpec] | None = None,
) -> dict[str, list[str]]:
    """启动校验：allowlist 中每个工具要么有实现，要么显式 UNAVAILABLE。"""
    table = dict(specs or default_specs())
    missing = sorted(
        name
        for name in DEFAULT_TOOL_ALLOWLIST
        if name not in table or not table[name].available
    )
    return {"available": sorted(name for name in table if table[name].available), "unavailable": missing}


class BoundToolRegistry(ToolRegistry):
    """在 allowlist 之上增加真实实现、schema、审批、限流与审计。"""

    def __init__(
        self,
        *,
        db: Session,
        project_id: int,
        actor_id: int | None = None,
        task_id: str | None = None,
        approval_token: str | None = None,
        specs: Mapping[str, ToolSpec] | None = None,
        allowlist: Mapping[str, tuple[str, ...]] | None = None,
        environment: str | None = None,
    ) -> None:
        self._specs = dict(specs or default_specs())
        for spec in self._specs.values():
            spec.validate()
        super().__init__(allowlist or DEFAULT_TOOL_ALLOWLIST, {})
        self._db = db
        self._project_id = int(project_id)
        self._actor_id = actor_id
        self._task_id = task_id
        self._approval_token = approval_token
        self._environment = str(environment or settings.environment)
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    # ── introspection ─────────────────────────────────
    def unavailable(self) -> list[str]:
        return sorted(name for name, spec in self._specs.items() if not spec.available)

    def spec(self, name: str) -> ToolSpec:
        spec = self._specs.get(str(name))
        if spec is None:
            raise ToolUnavailable(f"未注册工具: {name}")
        return spec

    def resolve(self, agent_key: str, tool_name: str) -> Callable[..., Any]:
        if tool_name not in self.allowed(agent_key):
            raise ToolNotAllowed(str(agent_key), tool_name)
        spec = self.spec(tool_name)
        if not spec.available:
            try:
                from app.aiqe.observability.metrics import metrics

                metrics.inc(
                    "aiqe_agent_tool_unavailable_total",
                    {"project_id": self._project_id, "tool": tool_name},
                )
            except Exception:
                pass
            raise ToolUnavailable(f"工具无真实实现: {tool_name}")
        return self._wrap(str(agent_key), spec)

    # ── invocation ────────────────────────────────────
    def _wrap(self, agent_key: str, spec: ToolSpec) -> Callable[..., Any]:
        def invoke(**kwargs: Any) -> Any:
            started = time.monotonic()
            approval_token = kwargs.pop("approval_token", None)
            try:
                self._precheck(agent_key, spec, kwargs, approval_token)
                result = self._call_with_timeout(spec, kwargs)
            except Exception as exc:
                self._audit(
                    agent_key,
                    spec,
                    kwargs,
                    decision="DENY",
                    reason=f"{type(exc).__name__}: {exc}"[:255],
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
                raise
            self._audit(
                agent_key,
                spec,
                kwargs,
                decision="ALLOW",
                reason="",
                result=result,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            return result

        return invoke

    def _precheck(
        self,
        agent_key: str,
        spec: ToolSpec,
        kwargs: Mapping[str, Any],
        approval_token: str | None,
    ) -> None:
        if spec.requires_human_approval or spec.side_effect_level != READ:
            if not approval_token or approval_token != self._approval_token:
                raise ToolApprovalRequired(f"{spec.name} 需要人工审批 token")
            if self._environment == "production" and spec.side_effect_level != READ:
                raise ToolPermissionError("生产环境默认只允许只读工具")
        if spec.secret_access_policy == "none":
            forbidden = [
                key
                for key in kwargs
                if any(word in key.lower() for word in ("secret", "password", "token", "private_key"))
            ]
            if forbidden:
                raise ToolSchemaError(f"工具不接受敏感字段: {sorted(forbidden)}")
        try:
            jsonschema.validate(dict(kwargs), dict(spec.input_schema))
        except jsonschema.ValidationError as exc:
            raise ToolSchemaError(f"参数 schema 校验失败: {exc.message}") from exc
        project_id = kwargs.get("project_id")
        if project_id is not None and int(project_id) != self._project_id:
            raise ToolPermissionError("工具 project_id 与当前 Project 不一致")
        bucket = self._calls[spec.name]
        now = time.monotonic()
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= int(spec.rate_limit_per_minute):
            raise ToolRateLimited(f"{spec.name} 超过限流 {spec.rate_limit_per_minute}/min")
        bucket.append(now)

    def _call_with_timeout(self, spec: ToolSpec, kwargs: Mapping[str, Any]) -> Any:
        assert spec.handler is not None
        payload = {**dict(kwargs), "project_id": self._project_id}
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(spec.handler, self._db, **payload)
            try:
                return future.result(timeout=float(spec.timeout_seconds))
            except FutureTimeout as exc:
                raise ToolTimeout(f"{spec.name} 执行超时 {spec.timeout_seconds}s") from exc

    def _audit(
        self,
        agent_key: str,
        spec: ToolSpec,
        kwargs: Mapping[str, Any],
        *,
        decision: str,
        reason: str,
        result: Any = None,
        duration_ms: int = 0,
    ) -> None:
        args_hash = "sha256:" + hashlib.sha256(
            json.dumps(dict(kwargs), sort_keys=True, default=str).encode()
        ).hexdigest()
        summary = {
            key: (value if isinstance(value, (int, float, bool)) or value is None else str(value)[:120])
            for key, value in list(kwargs.items())[:10]
        }
        evidence_refs: list[str] = []
        result_summary: dict[str, Any] = {}
        if isinstance(result, Mapping):
            result_summary = {
                str(key): (value if isinstance(value, (int, float, bool)) or value is None else str(value)[:120])
                for key, value in list(result.items())[:10]
            }
            evidence_refs = [str(item) for item in result.get("evidence_refs") or []]
        self._db.add(
            ToolExecutionAudit(
                project_id=self._project_id,
                actor_id=self._actor_id,
                agent_key=agent_key,
                task_id=self._task_id,
                tool_name=spec.name,
                tool_version=spec.version,
                side_effect_level=spec.side_effect_level,
                decision=decision,
                reason=str(reason or "")[:255],
                args_hash=args_hash,
                args_summary_json=summary,
                result_summary_json=result_summary,
                evidence_refs_json=evidence_refs,
                duration_ms=int(duration_ms),
            )
        )
        self._db.flush()


def build_bound_registry(
    db: Session,
    *,
    project_id: int,
    actor_id: int | None = None,
    task_id: str | None = None,
    approval_token: str | None = None,
    specs: Mapping[str, ToolSpec] | None = None,
) -> BoundToolRegistry:
    return BoundToolRegistry(
        db=db,
        project_id=project_id,
        actor_id=actor_id,
        task_id=task_id,
        approval_token=approval_token,
        specs=specs,
    )


__all__ = [
    "BoundToolRegistry",
    "ToolApprovalRequired",
    "ToolPermissionError",
    "ToolRateLimited",
    "ToolSchemaError",
    "ToolSpec",
    "ToolTimeout",
    "ToolUnavailable",
    "build_bound_registry",
    "default_specs",
    "validate_implementations",
]
