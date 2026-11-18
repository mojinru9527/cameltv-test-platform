"""AUD-005（capability preflight；与 main 的 FIX-005 preflight 并存）

原名 preflight.py；与 v1.4 FIX-005 的 `preflight.py` 合并时重命名，避免两套语义冲突。

AUD-005：Run / Node Preflight（Launch 前判定能力，缺能力直接 BLOCKED）。

v1.5 §01 AUD-005 第 5–6 条：

- ``PreflightService`` 按 Workflow 节点约束选择 Runner；检查在线、能力、版本、环境、
  凭据、网络和资源锁；
- 无匹配能力时 **Run 状态 BLOCKED，生成节点级 blocker，不创建空跑 Job**。

本模块只做确定性判断（不启动任何进程）。``INPROCESS_DRIVERS`` 是平台自身进程内可执行的
driver（http / db），仍受 AUD-001/002 的目标策略与查询登记约束；其余 driver 必须有
``VERIFIED``/``AVAILABLE`` 的外部节点。
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import capability_registry

#: driver → 必需的节点能力（v1.5 §03 AUD-020 平台覆盖）。
DRIVER_REQUIRED_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "": ("api.http",),
    "http": ("api.http",),
    "httpx": ("api.http",),
    "api": ("api.http",),
    "playwright": ("browser.chromium",),
    "web": ("browser.chromium",),
    "ui": ("browser.chromium",),
    "browser": ("browser.chromium",),
    "appium": ("device.android",),
    "android": ("device.android",),
    "ios": ("device.ios",),
    "mobile": ("mobile.app",),
    "db": ("db.readonly",),
    "db_readonly": ("db.readonly",),
    "database": ("db.readonly",),
    "miniapp": ("miniapp.wechat",),
    "desktop": ("desktop.app",),
    "iot": ("hardware.iot",),
    "device": ("device.android",),
    "external_e2e": ("external.e2e",),
}
#: 平台自身进程内即可执行，无需外部节点（仍受安全策略/查询登记约束）。
INPROCESS_DRIVERS: frozenset[str] = frozenset(
    {"", "http", "httpx", "api", "db", "db_readonly", "database"}
)


@dataclass(frozen=True)
class PreflightBlocker:
    code: str
    message: str
    node_key: str = ""
    driver: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "node_key": self.node_key,
            "driver": self.driver,
            "details": self.details,
        }


@dataclass(frozen=True)
class PreflightResult:
    allowed: bool
    status: str
    blockers: tuple[PreflightBlocker, ...] = ()
    checked_at: datetime | None = None
    required_capabilities: tuple[str, ...] = ()

    def payload(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "status": self.status,
            "checked_at": (self.checked_at or datetime.now(UTC)).isoformat(),
            "required_capabilities": list(self.required_capabilities),
            "blockers": [blocker.payload() for blocker in self.blockers],
        }


def required_capabilities_for(node_def: Mapping[str, Any]) -> tuple[str, ...]:
    driver = str(node_def.get("driver") or "").strip().lower()
    declared: list[str] = []
    single = str(node_def.get("capability") or "").strip()
    if single:
        declared.append(single)
    many = node_def.get("capabilities")
    if isinstance(many, (list, tuple)):
        declared.extend(str(item).strip() for item in many if str(item).strip())
    base = DRIVER_REQUIRED_CAPABILITIES.get(driver)
    if base is None:
        return tuple(sorted(set(declared)))
    return tuple(sorted({*base, *declared}))


def _check_production(db: Session, environment_id: int | None, allow_production: bool) -> PreflightBlocker | None:
    if environment_id is None or allow_production:
        return None
    from app.models.environment import Environment

    env = db.get(Environment, int(environment_id))
    if env is None:
        return PreflightBlocker("ENVIRONMENT_NOT_FOUND", f"环境不存在: {environment_id}")
    if bool(getattr(env, "is_production", False)):
        return PreflightBlocker(
            "PRODUCTION_EXECUTION_FORBIDDEN",
            "生产环境默认禁止 AIQE 自动执行业务 Workflow（只允许受控只读探测）",
            details={"environment_id": environment_id},
        )
    return None


def preflight_node(
    db: Session,
    *,
    node_def: Mapping[str, Any],
    environment_id: int | None = None,
    allow_production: bool = False,
    require_external_node: bool | None = None,
    now: datetime | None = None,
) -> PreflightResult:
    """单节点预检；``allowed=False`` 时调用方不得创建 Job。"""
    node_key = str(node_def.get("key") or "")
    driver = str(node_def.get("driver") or "").strip().lower()
    if driver not in DRIVER_REQUIRED_CAPABILITIES:
        return PreflightResult(
            allowed=False,
            status="BLOCKED",
            blockers=(
                PreflightBlocker(
                    "UNSUPPORTED_DRIVER",
                    f"未知 driver: {driver!r}",
                    node_key=node_key,
                    driver=driver,
                ),
            ),
            checked_at=now or datetime.now(UTC),
        )

    production_blocker = _check_production(db, environment_id, allow_production)
    if production_blocker is not None:
        return PreflightResult(
            allowed=False,
            status="BLOCKED",
            blockers=(production_blocker,),
            checked_at=now or datetime.now(UTC),
        )

    required = required_capabilities_for(node_def)
    capability_required = (
        bool(require_external_node) if require_external_node is not None else driver not in INPROCESS_DRIVERS
    )
    if not capability_required:
        return PreflightResult(
            allowed=True,
            status="READY",
            checked_at=now or datetime.now(UTC),
            required_capabilities=required,
        )

    candidates = capability_registry.select_nodes(db, required, now=now)
    platform = str(node_def.get("platform") or "").strip()
    if platform:
        candidates = [node_id for node_id in candidates if _node_has_platform(db, node_id, platform)]
    if not candidates:
        return PreflightResult(
            allowed=False,
            status="BLOCKED",
            blockers=(
                PreflightBlocker(
                    "NO_CAPABLE_RUNNER",
                    f"没有可用的 {driver} 执行节点（需要能力 {list(required)}"
                    + (f"、平台 {platform}" if platform else "")
                    + "）",
                    node_key=node_key,
                    driver=driver,
                    details={"required_capabilities": list(required), "platform": platform},
                ),
            ),
            checked_at=now or datetime.now(UTC),
            required_capabilities=required,
        )
    return PreflightResult(
        allowed=True,
        status="READY",
        checked_at=now or datetime.now(UTC),
        required_capabilities=required,
    )


def _node_has_platform(db: Session, node_id: str, platform: str) -> bool:
    row = db.scalar(
        select(NodeCapabilityManifest).where(NodeCapabilityManifest.node_id == node_id)
    )
    if row is None:
        return False
    platforms = {str(item).lower() for item in (row.platforms_json or [])}
    verified = {str(item).lower() for item in (row.verified_platforms_json or [])}
    return platform.lower() in platforms or platform.lower() in verified


def preflight_graph(
    db: Session,
    *,
    graph: Mapping[str, Any],
    environment_id: int | None = None,
    now: datetime | None = None,
) -> PreflightResult:
    """整图预检：任一节点不可执行即 BLOCKED，并返回全部 blocker。"""
    policy = graph.get("run_policy") or {}
    allow_production = bool(policy.get("allow_production", False))
    blockers: list[PreflightBlocker] = []
    required: set[str] = set()
    nodes = list(graph.get("nodes") or [])
    if not nodes:
        return PreflightResult(
            allowed=False,
            status="BLOCKED",
            blockers=(PreflightBlocker("EMPTY_WORKFLOW", "Workflow 没有任何节点"),),
            checked_at=now or datetime.now(UTC),
        )
    for node_def in nodes:
        if not isinstance(node_def, Mapping):
            blockers.append(PreflightBlocker("INVALID_NODE", "节点定义必须是对象"))
            continue
        result = preflight_node(
            db,
            node_def=node_def,
            environment_id=environment_id,
            allow_production=allow_production,
            now=now,
        )
        required.update(result.required_capabilities)
        blockers.extend(result.blockers)
    return PreflightResult(
        allowed=not blockers,
        status="READY" if not blockers else "BLOCKED",
        blockers=tuple(blockers),
        checked_at=now or datetime.now(UTC),
        required_capabilities=tuple(sorted(required)),
    )


def preflight_node_run(
    db: Session,
    node: NodeRun,
    *,
    run: TestRun | None = None,
    graph: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> PreflightResult:
    """执行前对 NodeRun 做同样预检（外部 runner 节点缺失时立刻 BLOCKED）。"""
    node_def: dict[str, Any] = {
        "key": node.node_key,
        "driver": node.driver_key,
        "input": dict(node.input_ref or {}),
    }
    policy = (graph or {}).get("run_policy") or {}
    return preflight_node(
        db,
        node_def=node_def,
        environment_id=getattr(run, "environment_id", None) if run is not None else None,
        allow_production=bool(policy.get("allow_production", False)),
        now=now,
    )


def requirement_reporter(
    db: Session, drivers: Iterable[str], *, now: datetime | None = None
) -> dict[str, list[str]]:
    """运维视图：某组 driver 分别缺哪些能力/节点。"""
    report: dict[str, list[str]] = {}
    for driver in drivers:
        key = str(driver or "").strip().lower()
        required = DRIVER_REQUIRED_CAPABILITIES.get(key, ())
        report[key] = capability_registry.select_nodes(db, required, now=now)
    return report


def schedule_guard(
    db: Session,
    *,
    run: TestRun,
    graph: Mapping[str, Any],
    on_blocked: Callable[[NodeRun, PreflightResult], None] | None = None,
) -> Callable[[NodeRun], bool]:
    """构造 ``dag_scheduler.schedule(preflight=...)`` 使用的守卫。"""

    def _guard(node: NodeRun) -> bool:
        result = preflight_node_run(db, node, run=run, graph=graph)
        if result.allowed:
            return True
        if on_blocked is not None:
            on_blocked(node, result)
        return False

    return _guard


__all__ = [
    "DRIVER_REQUIRED_CAPABILITIES",
    "INPROCESS_DRIVERS",
    "PreflightBlocker",
    "PreflightResult",
    "preflight_graph",
    "preflight_node",
    "preflight_node_run",
    "required_capabilities_for",
    "requirement_reporter",
    "schedule_guard",
]