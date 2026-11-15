"""FIX-005 / TA-015：Driver Capability Preflight。

Run 启动前必须回答：每个节点的 driver/capability/platform/node slot 是否真实可用；
缺失时 Run 直接 BLOCKED，并给出 node_key + required capability + available nodes，
不允许先 QUEUED、执行时才暴露 `UNSUPPORTED_DRIVER`。

能力状态：
- REGISTERED：有 manifest（DB 行存在）；
- AVAILABLE：heartbeat 有效 + evidence_ref 非空 + available=True；
- VERIFIED：manifest.last_evidence_ref 指向已保存的能力自检证据。
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.models.profile import ExecutionProfile
from app.aiqe.schemas.contracts import PreflightIssue, PreflightReport
from app.aiqe.services.run_context import EnvSecretProvider
from app.core.config import settings
from app.models.environment import Environment

HEARTBEAT_TTL_SECONDS = 30
VAR_RE = re.compile(r"\$\{([^{}]+)\}")
DRIVER_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "http": ("aiqe:http", "api.http"),
    "httpx": ("aiqe:http", "api.http"),
    "api": ("aiqe:http", "api.http"),
    "playwright": ("aiqe:playwright", "browser.chromium"),
    "web": ("aiqe:playwright", "browser.chromium"),
    "ui": ("aiqe:playwright", "browser.chromium"),
    "db": ("aiqe:db", "db.readonly"),
    "db_readonly": ("aiqe:db", "db.readonly"),
    "appium": ("aiqe:appium", "device.android"),
    "android": ("aiqe:appium", "device.android"),
    "mobile": ("aiqe:appium", "device.android"),
    "external_e2e": ("aiqe:external_e2e", "api.http"),
    "keploy": ("aiqe:keploy", "api.http"),
}
INPROCESS_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "http": ("aiqe:http", "api.http"),
    "httpx": ("aiqe:http", "api.http"),
    "api": ("aiqe:http", "api.http"),
}


def _heartbeat_fresh(row: NodeCapabilityManifest, *, now: datetime | None = None) -> bool:
    if row.last_heartbeat_at is None:
        return False
    heartbeat = row.last_heartbeat_at
    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=UTC)
    return (now or datetime.now(UTC)) - heartbeat <= timedelta(seconds=HEARTBEAT_TTL_SECONDS)


def available_manifests(db: Session) -> list[NodeCapabilityManifest]:
    rows = list(db.scalars(select(NodeCapabilityManifest)))
    now = datetime.now(UTC)
    return [row for row in rows if row.available and _heartbeat_fresh(row, now=now)]


def snapshot_manifests(db: Session) -> dict:
    rows = list(db.scalars(select(NodeCapabilityManifest)))
    now = datetime.now(UTC)
    return {
        row.node_id: {
            "driver_key": row.driver_key,
            "driver_version": row.driver_version,
            "capabilities": list(row.capabilities_json or []),
            "platforms": list(row.platforms_json or []),
            "max_parallel_sessions": row.max_parallel_sessions,
            "artifact_types": list(row.artifact_types_json or []),
            "available": bool(row.available),
            "heartbeat_fresh": _heartbeat_fresh(row, now=now),
            "evidence_ref": row.last_evidence_ref,
            "last_heartbeat_at": (
                row.last_heartbeat_at.isoformat() if row.last_heartbeat_at else ""
            ),
        }
        for row in rows
    }


def _required_capabilities(node: dict) -> tuple[str, ...]:
    explicit = str(node.get("capability") or "").strip()
    if explicit:
        return (explicit,)
    driver = str(node.get("driver") or "").strip().lower()
    return DRIVER_CAPABILITIES.get(driver, ())


def _node_matches(
    row: NodeCapabilityManifest,
    required: tuple[str, ...],
    *,
    platform: str = "",
) -> bool:
    caps = {str(item) for item in (row.capabilities_json or [])}
    if required and not any(cap in caps for cap in required):
        return False
    platforms = {str(item).strip().lower() for item in (row.platforms_json or [])}
    if platform and platforms and platform.lower() not in platforms:
        return False
    return True


def preflight_graph(
    db: Session,
    graph: dict,
    *,
    project_id: int | None = None,
    environment_id: int | None = None,
    profile_id: str | None = None,
    inprocess_enabled: bool | None = None,
    secret_provider: Any = None,
    fixtures: Mapping[str, Any] | None = None,
) -> PreflightReport:
    report = PreflightReport()
    rows = available_manifests(db)
    all_nodes = sorted(row.node_id for row in rows)
    enabled = (
        settings.aiqe_inprocess_executor_enabled
        if inprocess_enabled is None
        else inprocess_enabled
    )
    if environment_id is not None:
        environment = db.get(Environment, environment_id)
        if environment is None or (
            project_id is not None
            and int(environment.project_id or 0) != int(project_id)
        ):
            report.add(
                PreflightIssue(
                    node_key="__environment__",
                    code="ENVIRONMENT_MISSING",
                    message=f"环境不存在或不属于项目: {environment_id}",
                )
            )
    if profile_id:
        profile = db.get(ExecutionProfile, profile_id)
        if profile is None or (
            project_id is not None and int(profile.project_id or 0) != int(project_id)
        ):
            report.add(
                PreflightIssue(
                    node_key="__profile__",
                    code="PROFILE_MISSING",
                    message=f"Execution Profile 不存在或不属于项目: {profile_id}",
                )
            )
        elif profile.approval_status != "approved":
            report.add(
                PreflightIssue(
                    node_key="__profile__",
                    code="PROFILE_MISSING",
                    message=f"Execution Profile 未审批: {profile_id}",
                )
            )
    provider = secret_provider or EnvSecretProvider()
    fixture_values = dict(fixtures or {})
    for index, node in enumerate(graph.get("nodes") or []):
        if not isinstance(node, dict):
            report.add(
                PreflightIssue(
                    node_key=f"#{index}",
                    code="UNSUPPORTED_DRIVER",
                    message="节点不是对象",
                )
            )
            continue
        node_key = str(node.get("key") or f"#{index}")
        driver = str(node.get("driver") or "").strip().lower()
        required = _required_capabilities(node)
        if not required:
            report.add(
                PreflightIssue(
                    node_key=node_key,
                    code="UNSUPPORTED_DRIVER",
                    message=f"driver 不在能力注册表: {driver or '(空)'}",
                )
            )
            continue
        platform = str(node.get("platform") or "").strip()
        candidates = [
            row
            for row in rows
            if _node_matches(row, required, platform=platform)
        ]
        if not candidates:
            # 进程内 HTTP 执行器是受控特例：只有显式开启且是 http driver 才可用。
            if not (enabled and driver in INPROCESS_CAPABILITIES):
                report.add(
                    PreflightIssue(
                        node_key=node_key,
                        code="CAPABILITY_UNAVAILABLE",
                        message=(
                            f"没有可用节点覆盖 driver={driver} capability="
                            f"{'/'.join(required)}"
                        ),
                        required_capability="/".join(required),
                        available_nodes=all_nodes,
                    )
                )
                continue
        elif any(int(row.max_parallel_sessions or 0) <= 0 for row in candidates):
            report.add(
                PreflightIssue(
                    node_key=node_key,
                    code="NO_SLOT",
                    message="候选节点 max_parallel_sessions <= 0",
                    required_capability="/".join(required),
                    available_nodes=[row.node_id for row in candidates],
                )
            )
        # Secret / fixture 引用必须在启动前可解析，不能等执行时才失败。
        for text in _iter_strings(node.get("input")):
            match = VAR_RE.fullmatch(text)
            if not match:
                continue
            ref = match.group(1)
            if ref.startswith("secrets."):
                key = ref.split(".", 1)[1]
                if provider.get(key) is None:
                    report.add(
                        PreflightIssue(
                            node_key=node_key,
                            code="SECRET_MISSING",
                            message=f"secret 未注入: {key}",
                        )
                    )
            elif ref.upper().startswith("SECRET:"):
                key = ref.split(":", 1)[1]
                if provider.get(key) is None:
                    report.add(
                        PreflightIssue(
                            node_key=node_key,
                            code="SECRET_MISSING",
                            message=f"secret 未注入: {key}",
                        )
                    )
            elif ref.upper().startswith("FIXTURE:"):
                key = ref.split(":", 1)[1]
                if key not in fixture_values:
                    report.add(
                        PreflightIssue(
                            node_key=node_key,
                            code="FIXTURE_MISSING",
                            message=f"fixture 不存在: {key}",
                        )
                    )
    return report


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
