"""AUD-001：服务端目标访问策略（Target Policy）。

设计原则（v1.5 §01 AUD-001）：

1. **策略由服务端拥有**：`TargetPolicyResolver.resolve()` 只从已授权的
   `aiqe_target_policies` / `environment` 配置读取，**不接受** Workflow、Agent 或
   请求体传入的覆盖项（`allow_private` / `allowed_hosts` / `proxy` / `verify_tls`）。
2. **默认拒绝**：没有配置策略时返回 `deny_all`，任何目标都解析为 BLOCKED。
3. **可审计**：策略带 `version`，拒绝事件记录 `policy_version` 与来源。
4. **私网需显式授权**：回环 / 私网 / 链路本地 / 保留地址默认拒绝，只有管理员把网段
   写入 `allow_private_cidrs` 才放行；`blocked_cidrs`（云元数据等）优先级最高。

本模块不导入 settings，保持可离线单测。
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import select
from sqlalchemy.orm import Session

if TYPE_CHECKING:  # pragma: no cover - 仅类型检查
    from app.aiqe.models.security import TargetPolicyRecord

DEFAULT_SCHEMES: tuple[str, ...] = ("http", "https")
DEFAULT_METHODS: tuple[str, ...] = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
DEFAULT_PORTS: tuple[int, ...] = (80, 443)

#: 任何策略都无法放行的地址段（云元数据、链路本地、CGNAT、保留段）。
#: 注意：回环（127.0.0.0/8、::1）与私网（10/8、172.16/12、192.168/16、fc00::/7）**不在**
#: 这个名单里 —— 它们由 `is_global` 默认拒绝，只有管理员写进 `allow_private_cidrs`
#: 才放行（v1.5 AUD-001「除非管理员对专用测试网络显式授权」）。
DEFAULT_BLOCKED_CIDRS: tuple[str, ...] = (
    "169.254.0.0/16",  # link-local + 云元数据 169.254.169.254
    "100.64.0.0/10",  # CGNAT
    "192.0.0.0/24",  # IETF protocol assignments
    "198.18.0.0/15",  # 基准测试网段
    "240.0.0.0/4",  # 保留
    "0.0.0.0/8",  # 本网络
    "fe80::/10",  # IPv6 链路本地（必须带 zone id 才可用，一体拒绝）
    "64:ff9b::/96",  # NAT64（可把任意 IPv4 映射进 IPv6）
)

MIN_REDIRECTS = 0
MAX_REDIRECTS = 10
DEFAULT_MAX_REQUEST_BYTES = 1024 * 1024
DEFAULT_MAX_RESPONSE_BYTES = 512 * 1024
DEFAULT_CONNECT_TIMEOUT_MS = 5000
DEFAULT_READ_TIMEOUT_MS = 15000

#: 解析后的授权有效期（秒）。Worker 每次 claim/重试都必须重新解析，
#: 过期授权不得沿用（V16-001 §8）。
DEFAULT_POLICY_TTL_SECONDS = 300

#: 策略哈希算法版本；变更判定字段时必须同步升级。
POLICY_HASH_SCHEMA = "aiqe.target-policy.v1"


class PolicyDecision(str, Enum):
    """V16-001：显式的四态策略决策，禁止用 bool 表达“是否有策略”。"""

    ALLOW = "ALLOW"
    DENY = "DENY"
    UNAVAILABLE = "UNAVAILABLE"
    MISSING_BINDING = "MISSING_BINDING"


@dataclass(frozen=True)
class ExecutionCapabilities:
    """节点能力声明（不是授权）。

    V16-001 要求 ``execute_node()`` 的 ``policy_context`` 必须是显式对象：
    需要网络/DB/浏览器/设备能力的节点只能提交 ``ResolvedExecutionPolicy``；
    纯本地节点用 ``ExecutionCapabilities.NONE`` 明确声明“不发起任何外部动作”，
    不允许用 ``None`` 表示绕过。
    """

    network: bool = False
    db_read: bool = False
    browser: bool = False
    device: bool = False

    NONE: ClassVar[ExecutionCapabilities]


ExecutionCapabilities.NONE = ExecutionCapabilities()


class TargetPolicyConfigError(ValueError):
    """策略配置本身非法（例如非法 CIDR / 端口）。"""


def _as_tuple(values: Iterable[Any] | None) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    return tuple(values)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_networks(values: Iterable[str] | None, *, field_name: str) -> tuple[Any, ...]:
    networks: list[Any] = []
    for raw in _as_tuple(values):
        text = str(raw).strip()
        if not text:
            continue
        try:
            networks.append(ipaddress.ip_network(text, strict=False))
        except ValueError as exc:
            raise TargetPolicyConfigError(f"{field_name} 非法 CIDR: {text}") from exc
    return tuple(networks)


def _parse_ports(values: Iterable[Any] | None) -> tuple[int, ...]:
    ports: list[int] = []
    for raw in _as_tuple(values):
        try:
            port = int(raw)
        except (TypeError, ValueError) as exc:
            raise TargetPolicyConfigError(f"allowed_ports 非法端口: {raw!r}") from exc
        if not 1 <= port <= 65535:
            raise TargetPolicyConfigError(f"allowed_ports 端口越界: {port}")
        ports.append(port)
    return tuple(sorted(set(ports)))


def _normalize_host_pattern(host: str) -> str:
    text = str(host).strip().lower().rstrip(".")
    return text


@dataclass(frozen=True)
class TargetPolicy:
    """不可变的目标访问策略快照（V16-001 的 ``ResolvedExecutionPolicy``）。

    ``decision`` 是唯一授权判定入口：只有 ``PolicyDecision.ALLOW`` 才允许创建
    Driver / 发起网络或数据库动作；任何其他取值都必须 BLOCKED。
    """

    project_id: int | None = None
    environment_id: int | None = None
    version: int = 0
    source: str = "deny_all"
    allowed_hosts: tuple[str, ...] = ()
    allowed_ports: tuple[int, ...] = ()
    allowed_schemes: tuple[str, ...] = DEFAULT_SCHEMES
    allow_private_cidrs: tuple[str, ...] = ()
    blocked_cidrs: tuple[str, ...] = DEFAULT_BLOCKED_CIDRS
    allowed_methods: tuple[str, ...] = DEFAULT_METHODS
    max_redirects: int = MIN_REDIRECTS
    allow_cross_host_redirect: bool = False
    verify_tls: bool = True
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    connect_timeout_ms: int = DEFAULT_CONNECT_TIMEOUT_MS
    read_timeout_ms: int = DEFAULT_READ_TIMEOUT_MS
    deny_reason: str = ""
    #: V16-001 新增：显式决策与可审计元数据。
    decision: PolicyDecision = PolicyDecision.DENY
    policy_id: str | None = None
    policy_hash: str = ""
    reason_code: str | None = None
    expires_at: datetime | None = None
    resolved_addresses: tuple[str, ...] = ()
    _allowed_networks: tuple[Any, ...] = field(default=(), repr=False, compare=False)
    _blocked_networks: tuple[Any, ...] = field(default=(), repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "allowed_hosts",
            tuple(
                pattern
                for pattern in (_normalize_host_pattern(h) for h in self.allowed_hosts)
                if pattern
            ),
        )
        object.__setattr__(self, "allowed_ports", _parse_ports(self.allowed_ports))
        object.__setattr__(
            self,
            "allowed_schemes",
            tuple(sorted({str(s).strip().lower() for s in self.allowed_schemes if str(s).strip()})),
        )
        object.__setattr__(
            self,
            "allowed_methods",
            tuple(sorted({str(m).strip().upper() for m in self.allowed_methods if str(m).strip()})),
        )
        object.__setattr__(
            self,
            "_allowed_networks",
            _parse_networks(self.allow_private_cidrs, field_name="allow_private_cidrs"),
        )
        object.__setattr__(
            self,
            "_blocked_networks",
            _parse_networks(self.blocked_cidrs, field_name="blocked_cidrs"),
        )
        object.__setattr__(self, "max_redirects", max(MIN_REDIRECTS, min(int(self.max_redirects), MAX_REDIRECTS)))
        object.__setattr__(self, "max_request_bytes", max(1, int(self.max_request_bytes)))
        object.__setattr__(self, "max_response_bytes", max(1, int(self.max_response_bytes)))
        object.__setattr__(self, "connect_timeout_ms", max(1, int(self.connect_timeout_ms)))
        object.__setattr__(self, "read_timeout_ms", max(1, int(self.read_timeout_ms)))

        decision = self.decision
        if not isinstance(decision, PolicyDecision):
            decision = PolicyDecision(str(decision))
        if decision is not PolicyDecision.ALLOW and self.allowed_hosts:
            # 非 ALLOW 决策不得携带可用白名单，避免调用方误用字段绕过判定。
            object.__setattr__(self, "allowed_hosts", ())
        if self.policy_hash == "":
            object.__setattr__(self, "policy_hash", self.compute_hash())

    def compute_hash(self) -> str:
        """稳定 hash：只覆盖授权判定字段，不含解析时间/地址。"""
        payload = {
            "schema": POLICY_HASH_SCHEMA,
            "decision": self.decision.value,
            "reason_code": self.reason_code,
            "source": self.source,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "policy_id": self.policy_id,
            "version": self.version,
            "allowed_hosts": list(self.allowed_hosts),
            "allowed_ports": list(self.allowed_ports),
            "allowed_schemes": list(self.allowed_schemes),
            "allow_private_cidrs": list(self.allow_private_cidrs),
            "blocked_cidrs": list(self.blocked_cidrs),
            "allowed_methods": list(self.allowed_methods),
            "max_redirects": self.max_redirects,
            "allow_cross_host_redirect": self.allow_cross_host_redirect,
            "verify_tls": self.verify_tls,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ── 查询 ────────────────────────────────────────────────
    @property
    def allowed_networks(self) -> tuple[Any, ...]:
        return self._allowed_networks

    @property
    def blocked_networks(self) -> tuple[Any, ...]:
        return self._blocked_networks

    @property
    def is_deny_all(self) -> bool:
        return not self.allowed_hosts

    def allows_host(self, hostname: str) -> bool:
        """主机白名单匹配：精确匹配或 ``*.suffix`` 子域通配。"""
        host = _normalize_host_pattern(hostname)
        if not host:
            return False
        for pattern in self.allowed_hosts:
            if pattern == host:
                return True
            if pattern.startswith("*."):
                suffix = pattern[1:]  # ".example.com"
                if host.endswith(suffix) and len(host) > len(suffix):
                    return True
            elif pattern.startswith(".") and host.endswith(pattern) and len(host) > len(pattern):
                return True
        return False

    def snapshot(self) -> dict[str, Any]:
        """可持久化 / 可展示的策略快照（不含运行时对象）。"""
        return {
            "decision": self.decision.value,
            "policy_id": self.policy_id,
            "policy_hash": self.policy_hash,
            "reason_code": self.reason_code,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "policy_version": self.version,
            "policy_source": self.source,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "allowed_hosts": list(self.allowed_hosts),
            "allowed_ports": list(self.allowed_ports),
            "allowed_schemes": list(self.allowed_schemes),
            "allow_private_cidrs": list(self.allow_private_cidrs),
            "blocked_cidrs": list(self.blocked_cidrs),
            "allowed_methods": list(self.allowed_methods),
            "max_redirects": self.max_redirects,
            "allow_cross_host_redirect": self.allow_cross_host_redirect,
            "verify_tls": self.verify_tls,
            "max_request_bytes": self.max_request_bytes,
            "max_response_bytes": self.max_response_bytes,
            "connect_timeout_ms": self.connect_timeout_ms,
            "read_timeout_ms": self.read_timeout_ms,
            "resolved_addresses": list(self.resolved_addresses),
            "deny_reason": self.deny_reason,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None, **kwargs: Any) -> TargetPolicy:
        """从 ``policy_json`` 构造；未知键忽略，非法值 fail closed。"""
        payload = dict(data or {})
        allowed_private = payload.get("allow_private")
        if allowed_private not in (None, False) and not payload.get("allow_private_cidrs"):
            # 历史/外部配置里若只写了 allow_private=True，等价于授权全部私网；这里显式
            # 展开成网段，保持"CIDR 授权"是唯一可审计的放行方式。
            payload["allow_private_cidrs"] = [
                "10.0.0.0/8",
                "172.16.0.0/12",
                "192.168.0.0/16",
                "127.0.0.0/8",
                "::1/128",
            ]
        fields: dict[str, Any] = {
            "allowed_hosts": _as_tuple(payload.get("allowed_hosts")),
            "allowed_ports": _as_tuple(payload.get("allowed_ports")),
            "allow_private_cidrs": _as_tuple(payload.get("allow_private_cidrs")),
            "allowed_methods": _as_tuple(payload.get("allowed_methods")) or DEFAULT_METHODS,
        }
        for key in (
            "max_redirects",
            "allow_cross_host_redirect",
            "verify_tls",
            "max_request_bytes",
            "max_response_bytes",
            "connect_timeout_ms",
            "read_timeout_ms",
        ):
            if payload.get(key) is not None:
                fields[key] = payload[key]
        if payload.get("allowed_schemes"):
            fields["allowed_schemes"] = _as_tuple(payload.get("allowed_schemes"))
        if payload.get("blocked_cidrs") is not None:
            fields["blocked_cidrs"] = _as_tuple(payload.get("blocked_cidrs"))
        else:
            fields["blocked_cidrs"] = DEFAULT_BLOCKED_CIDRS
        fields.update({k: v for k, v in kwargs.items() if v is not None})
        return cls(**fields)

    @classmethod
    def from_snapshot(cls, data: Mapping[str, Any] | None) -> TargetPolicy:
        """从 ``snapshot()`` 输出重建策略（外部 Runner 解析服务端下发的快照）。

        - ``decision`` 必须是已知枚举值，未知一律 DENY；
        - ``expires_at`` 解析失败 → None（由执行器按“无有效期”处理，仍在 ALLOW 前校验决策）；
        - 快照中的 ``policy_hash`` 若存在则保留，便于跨进程核对同一策略版本。
        """
        payload = dict(data or {})
        decision_raw = str(payload.get("decision") or "").strip().upper()
        try:
            decision = PolicyDecision(decision_raw)
        except ValueError:
            decision = PolicyDecision.DENY
        expires_at: datetime | None = None
        expires_raw = payload.get("expires_at")
        if isinstance(expires_raw, str) and expires_raw:
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None
        version_raw = payload.get("policy_version", payload.get("version", 0))
        try:
            version = int(version_raw or 0)
        except (TypeError, ValueError):
            version = 0
        return cls(
            project_id=_optional_int(payload.get("project_id")),
            environment_id=_optional_int(payload.get("environment_id")),
            version=version,
            source=str(payload.get("policy_source") or "external_snapshot"),
            allowed_hosts=_as_tuple(payload.get("allowed_hosts")),
            allowed_ports=_as_tuple(payload.get("allowed_ports")),
            allowed_schemes=_as_tuple(payload.get("allowed_schemes")) or DEFAULT_SCHEMES,
            allow_private_cidrs=_as_tuple(payload.get("allow_private_cidrs")),
            blocked_cidrs=_as_tuple(payload.get("blocked_cidrs")) or DEFAULT_BLOCKED_CIDRS,
            allowed_methods=_as_tuple(payload.get("allowed_methods")) or DEFAULT_METHODS,
            max_redirects=int(payload.get("max_redirects") or 0),
            allow_cross_host_redirect=bool(payload.get("allow_cross_host_redirect") or False),
            verify_tls=bool(payload.get("verify_tls", True)),
            decision=decision,
            policy_id=payload.get("policy_id"),
            policy_hash=str(payload.get("policy_hash") or ""),
            reason_code=payload.get("reason_code") or payload.get("deny_reason"),
            expires_at=expires_at,
            deny_reason=str(payload.get("deny_reason") or ""),
        )

    @classmethod
    def deny_all(
        cls,
        *,
        project_id: int | None = None,
        environment_id: int | None = None,
        reason: str = "NO_POLICY_CONFIGURED",
        source: str = "deny_all",
        decision: PolicyDecision = PolicyDecision.DENY,
    ) -> TargetPolicy:
        return cls(
            project_id=project_id,
            environment_id=environment_id,
            version=0,
            source=source,
            allowed_hosts=(),
            deny_reason=reason,
            decision=decision,
            reason_code=reason,
        )


class TargetPolicyResolver:
    """按 project/environment 解析服务端策略；**不接受**调用方覆盖。"""

    def __init__(self, db: Session | None = None) -> None:
        self._db = db

    def resolve(
        self,
        *,
        project_id: int,
        environment_id: int | None = None,
        now: datetime | None = None,
    ) -> TargetPolicy:
        """解析策略并返回**显式决策**的不可变快照。

        决策语义（V16-001）：
        - ``ALLOW``：存在服务端策略或 Environment 绑定的目标，且具备可验证约束；
        - ``DENY``：管理员显式配置为空 / 目标不在策略内；
        - ``UNAVAILABLE``：策略存储或安全服务不可用（DB 会话缺失、查询异常）；
        - ``MISSING_BINDING``：Run 未绑定 Project/Environment/Policy。
        """
        project = int(project_id)
        env_id = int(environment_id) if environment_id is not None else None
        expires = (now or datetime.now(UTC)) + timedelta(seconds=DEFAULT_POLICY_TTL_SECONDS)
        if self._db is None:
            return TargetPolicy.deny_all(
                project_id=project,
                environment_id=env_id,
                reason="POLICY_STORE_UNAVAILABLE",
                decision=PolicyDecision.UNAVAILABLE,
            )

        from app.aiqe.models.security import TargetPolicyRecord

        # 查询异常必须上抛，由 resolve_execution_policy 统一转成 UNAVAILABLE；
        # 绝不能在异常时返回“空策略”让调用方误判为 DENY 后又被 legacy 路径兜底。
        rows = list(
            self._db.scalars(
                select(TargetPolicyRecord).where(
                    TargetPolicyRecord.project_id == project,
                    TargetPolicyRecord.active.is_(True),
                )
            )
        )
        env_rows = [row for row in rows if env_id is not None and row.environment_id == env_id]
        wide_rows = [row for row in rows if row.environment_id is None]
        candidates = env_rows or wide_rows
        if candidates:
            chosen = max(candidates, key=lambda row: int(row.version or 0))
            policy_json = dict(chosen.policy_json or {})
            blocked_flag = str(policy_json.get("decision") or "").strip().upper()
            if bool(policy_json.get("deny_all")) or blocked_flag == PolicyDecision.DENY.value:
                # 管理员显式拒绝：即使其他字段配了白名单也不得执行。
                return TargetPolicy.deny_all(
                    project_id=project,
                    environment_id=chosen.environment_id,
                    reason="EXPLICIT_DENY",
                    decision=PolicyDecision.DENY,
                )
            # 显式策略存在即代表管理员已授权该 project/environment 执行；
            # 具体目标是否可达仍由 allowed_hosts/ports（HTTP）或 Query Registry（DB）逐项判定。
            return TargetPolicy.from_mapping(
                policy_json,
                project_id=project,
                environment_id=chosen.environment_id,
                version=int(chosen.version or 1),
                source=f"policy_record:{chosen.id}",
                policy_id=str(chosen.id),
                decision=PolicyDecision.ALLOW,
                expires_at=expires,
            )

        # V16-001：环境 base_url 不是“服务端策略”，不能替代管理员授权。
        # 没有 TargetPolicyRecord 时一律拒绝（旧环境需先迁移策略）。
        reason = "NO_POLICY_CONFIGURED" if env_id is not None else "RUN_ENVIRONMENT_MISSING"
        return TargetPolicy.deny_all(
            project_id=project,
            environment_id=env_id,
            reason=reason,
            decision=PolicyDecision.MISSING_BINDING,
        )


def resolve_execution_policy(
    db: Session | None,
    run: Any = None,
    node: Any = None,
    *,
    project_id: int | None = None,
    environment_id: int | None = None,
    now: datetime | None = None,
) -> TargetPolicy:
    """V16-001 正式入口：在创建任何 Driver 前解析 Run 的执行策略。

    任何异常（DB 不可用、策略表缺失、非法配置）都转成 ``UNAVAILABLE``，
    调用方只能 BLOCKED，不得降级到 legacy executor。
    """
    bound_project = project_id
    bound_environment = environment_id
    if run is not None:
        if bound_project is None:
            bound_project = getattr(run, "project_id", None)
        if bound_environment is None:
            bound_environment = getattr(run, "environment_id", None)
    if node is not None and bound_project is None:
        bound_project = getattr(node, "project_id", None)
    try:
        project = int(bound_project) if bound_project is not None else None
    except (TypeError, ValueError):
        project = None
    if project is None:
        return TargetPolicy.deny_all(
            project_id=None,
            environment_id=None,
            reason="RUN_PROJECT_MISSING",
            decision=PolicyDecision.MISSING_BINDING,
        )
    try:
        return TargetPolicyResolver(db).resolve(
            project_id=project,
            environment_id=bound_environment,
            now=now,
        )
    except Exception:
        # 统一 fail closed；错误细节由调用方写入安全事件（不包含敏感配置）。
        return TargetPolicy.deny_all(
            project_id=project,
            environment_id=environment_id,
            reason="POLICY_RESOLVE_ERROR",
            decision=PolicyDecision.UNAVAILABLE,
        )


def upsert_target_policy(
    db: Session,
    *,
    project_id: int,
    environment_id: int | None,
    policy: Mapping[str, Any],
    name: str = "default",
    created_by: int | None = None,
    base_version: int | None = None,
) -> TargetPolicyRecord:
    """写入新版本策略（旧版本保持只读，用于审计与回滚）。

    ``base_version`` 提供乐观锁：与当前最大版本不一致时抛 ``TargetPolicyConfigError``，
    避免两个管理员并发写入同一版本号。
    """
    from app.aiqe.models.security import TargetPolicyRecord

    if not isinstance(policy, Mapping):
        raise TargetPolicyConfigError("policy 必须是对象")
    # 构造一次以校验合法性（非法 CIDR / 端口在这里就 fail closed）
    TargetPolicy.from_mapping(policy, project_id=project_id, environment_id=environment_id)

    # 同一 project/environment 只允许一条 active 策略；旧行保留（active=False）用于审计。
    existing = list(
        db.scalars(
            select(TargetPolicyRecord).where(
                TargetPolicyRecord.project_id == int(project_id),
                TargetPolicyRecord.environment_id == environment_id,
            )
        )
    )
    current_version = max((int(row.version or 0) for row in existing), default=0)
    if base_version is not None and int(base_version) != current_version:
        raise TargetPolicyConfigError(
            f"策略版本冲突：期望 {base_version}，当前 {current_version}"
        )
    for row in existing:
        if row.active:
            row.active = False
    record = TargetPolicyRecord(
        project_id=int(project_id),
        environment_id=environment_id,
        name=name,
        version=current_version + 1,
        policy_json=dict(policy),
        active=True,
        created_by=created_by,
    )
    db.add(record)
    db.flush()
    return record


__all__ = [
    "DEFAULT_BLOCKED_CIDRS",
    "DEFAULT_METHODS",
    "DEFAULT_POLICY_TTL_SECONDS",
    "DEFAULT_SCHEMES",
    "ExecutionCapabilities",
    "POLICY_HASH_SCHEMA",
    "PolicyDecision",
    "ResolvedExecutionPolicy",
    "TargetPolicy",
    "TargetPolicyConfigError",
    "TargetPolicyResolver",
    "resolve_execution_policy",
    "upsert_target_policy",
]

#: V16-001 规格命名：解析后的执行策略即 ``ResolvedExecutionPolicy``。
#: 保留 ``TargetPolicy`` 作为同一不可变类型的兼容别名（禁止再建第二套策略类型）。
ResolvedExecutionPolicy = TargetPolicy
