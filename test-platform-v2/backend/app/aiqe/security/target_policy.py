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

import ipaddress
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

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


class TargetPolicyConfigError(ValueError):
    """策略配置本身非法（例如非法 CIDR / 端口）。"""


def _as_tuple(values: Iterable[Any] | None) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    return tuple(values)


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
    """不可变的目标访问策略快照。"""

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
    def deny_all(
        cls,
        *,
        project_id: int | None = None,
        environment_id: int | None = None,
        reason: str = "NO_POLICY_CONFIGURED",
        source: str = "deny_all",
    ) -> TargetPolicy:
        return cls(
            project_id=project_id,
            environment_id=environment_id,
            version=0,
            source=source,
            allowed_hosts=(),
            deny_reason=reason,
        )


def _host_port_from_base_url(base_url: str) -> tuple[str, int] | None:
    try:
        parsed = urlsplit(str(base_url or "").strip())
    except ValueError:
        return None
    if parsed.scheme not in DEFAULT_SCHEMES or not parsed.hostname:
        return None
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None
    return parsed.hostname, port


class TargetPolicyResolver:
    """按 project/environment 解析服务端策略；**不接受**调用方覆盖。"""

    def __init__(self, db: Session | None = None) -> None:
        self._db = db

    def resolve(
        self, *, project_id: int, environment_id: int | None = None
    ) -> TargetPolicy:
        project = int(project_id)
        env_id = int(environment_id) if environment_id is not None else None
        if self._db is None:
            return TargetPolicy.deny_all(
                project_id=project, environment_id=env_id, reason="NO_POLICY_SESSION"
            )

        from app.aiqe.models.security import TargetPolicyRecord

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
            return TargetPolicy.from_mapping(
                chosen.policy_json,
                project_id=project,
                environment_id=chosen.environment_id,
                version=int(chosen.version or 1),
                source=f"policy_record:{chosen.id}",
            )

        # 兼容路径：没有显式策略时，只授权该 Environment 自己的 base_url（被测系统），
        # 且仍走私网/端口/方法检查；这不是"放开私网"。
        base = self._environment_target(env_id)
        if base is not None:
            host, port = base
            return TargetPolicy(
                project_id=project,
                environment_id=env_id,
                version=0,
                source="environment_base_url",
                allowed_hosts=(host,),
                allowed_ports=(port,),
                max_redirects=0,
            )
        return TargetPolicy.deny_all(project_id=project, environment_id=env_id)

    def _environment_target(self, environment_id: int | None) -> tuple[str, int] | None:
        if self._db is None or environment_id is None:
            return None
        from app.models.environment import Environment

        env = self._db.get(Environment, int(environment_id))
        if env is None:
            return None
        return _host_port_from_base_url(getattr(env, "base_url", "") or "")


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
    "DEFAULT_SCHEMES",
    "TargetPolicy",
    "TargetPolicyConfigError",
    "TargetPolicyResolver",
    "upsert_target_policy",
]
