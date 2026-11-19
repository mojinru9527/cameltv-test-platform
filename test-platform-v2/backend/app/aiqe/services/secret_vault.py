"""AUD-003：Secret Handle 读写服务（进程内 Vault + DB 元信息）。

契约（v1.5 §01 AUD-003 / §06 3.1）：

- 明文只在执行期短暂存在于进程内 Vault，**不进入 DB、Event、Artifact、Prompt**；
- Handle 元信息绑定 ``project_id / run_id / producer_node_run_id /
  allowed_consumer_nodes / expires_at``；
- 下游解析必须同时满足：同 project、同 Run、节点在允许消费列表中、未过期、未撤销；
- 跨 Project / 跨 Run / 非 DAG 下游 / 过期 / 已撤销 → ``SecretAccessDenied``（HTTP 层映射 403/404）。
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.secret_handle import SecretAccessAudit, SecretHandle

DEFAULT_TTL_SECONDS = 900
MAX_TTL_SECONDS = 24 * 3600
VAULT_REF_PREFIX = "vault://"

#: 字段名 → secret_type（用于审计与轮换策略，不作为唯一判定依据）。
_SECRET_TYPE_HINTS: tuple[tuple[str, str], ...] = (
    ("refresh", "refresh_token"),
    ("access_token", "access_token"),
    ("jwt", "jwt"),
    ("id_token", "jwt"),
    ("cookie", "cookie"),
    ("password", "password"),
    ("passwd", "password"),
    ("api_key", "api_key"),
    ("apikey", "api_key"),
    ("private_key", "private_key"),
    ("client_secret", "client_secret"),
    ("token", "token"),
)


class SecretHandleError(ValueError):
    """Handle 创建参数非法。"""


class SecretAccessDenied(PermissionError):
    """Handle 不可被当前 actor/node 解析（403/404 语义）。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class SecretVaultUnavailable(RuntimeError):
    """Vault 后端不可用：调用方必须 fail closed（不得回退明文）。"""


def secret_type_for_key(key_name: str, value: str = "") -> str:
    text = str(key_name or "").strip().lower()
    for hint, secret_type in _SECRET_TYPE_HINTS:
        if hint in text:
            return secret_type
    if value.startswith("eyJ") and value.count(".") == 2:
        return "jwt"
    return "generic"


class SecretVaultBackend(Protocol):
    """Vault 后端契约：生产实现必须支持 KMS/envelope 与跨进程解析。"""

    def put(
        self, *, handle_id: str, value: str, expires_at: datetime, run_id: str, project_id: int
    ) -> None: ...

    def get(self, handle_id: str) -> _Entry | None: ...

    def drop(self, handle_id: str) -> None: ...

    def purge_expired(self, *, now: datetime | None = None) -> int: ...

    def clear(self) -> None: ...


@dataclass(frozen=True)
class _Entry:
    value: str
    expires_at: datetime
    run_id: str
    project_id: int


class SecretVault:
    """进程内短期明文存储；进程重启即失效（fail closed）。

    仅用于开发/测试；生产必须替换为 KMS/Secret Manager 实现
    （``settings.use_external_secret_store`` 为 True 时本实现拒绝启动）。
    """

    def __init__(self, *, backend: str = "memory") -> None:
        self.backend = backend
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.RLock()

    def put(self, *, handle_id: str, value: str, expires_at: datetime, run_id: str, project_id: int) -> None:
        with self._lock:
            self._entries[handle_id] = _Entry(
                value=value, expires_at=expires_at, run_id=run_id, project_id=project_id
            )

    def get(self, handle_id: str) -> _Entry | None:
        with self._lock:
            return self._entries.get(handle_id)

    def drop(self, handle_id: str) -> None:
        with self._lock:
            self._entries.pop(handle_id, None)

    def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or datetime.now(UTC)
        with self._lock:
            expired = [key for key, entry in self._entries.items() if entry.expires_at <= moment]
            for key in expired:
                self._entries.pop(key, None)
        return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


VAULT = SecretVault()


def get_secret_vault() -> SecretVault:
    """Vault 提供者：外部 Secret Store 未实现时必须 fail closed。"""
    from app.core.config import settings

    if bool(getattr(settings, "use_external_secret_store", False)):
        raise SecretVaultUnavailable(
            "AIQE 外部 Secret Store 尚未实现：禁止在未配置 KMS/Secret Manager 时执行敏感节点"
        )
    return VAULT


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _audit_access(
    db: Session,
    *,
    row: SecretHandle,
    consumer_node_key: str,
    decision: str,
    reason_code: str,
    now: datetime,
) -> str:
    audit = SecretAccessAudit(
        handle_id=row.id,
        project_id=int(row.project_id),
        run_id=str(row.run_id),
        consumer_node_key=str(consumer_node_key or ""),
        decision=decision,
        reason_code=reason_code,
        created_at=now,
    )
    db.add(audit)
    db.flush()
    return str(audit.id)


def create_secret_handle(
    db: Session,
    *,
    project_id: int,
    run_id: str,
    producer_node_run_id: str,
    key_name: str,
    value: str,
    allowed_consumer_nodes: list[str] | tuple[str, ...] = (),
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    metadata: dict[str, Any] | None = None,
    vault: SecretVault | None = None,
    now: datetime | None = None,
    secret_type: str | None = None,
    consumer_scope: dict[str, Any] | None = None,
    rotation_version: int = 1,
) -> SecretHandle:
    if not str(key_name or "").strip():
        raise SecretHandleError("key_name 不能为空")
    if not isinstance(value, str) or not value:
        raise SecretHandleError("secret value 不能为空")
    ttl = int(ttl_seconds or DEFAULT_TTL_SECONDS)
    if not 1 <= ttl <= MAX_TTL_SECONDS:
        raise SecretHandleError(f"ttl_seconds 必须在 1..{MAX_TTL_SECONDS}")
    run = db.get(TestRun, str(run_id))
    if run is None or int(run.project_id) != int(project_id):
        raise SecretHandleError("run 不存在或不属于该 Project")
    node = db.get(NodeRun, str(producer_node_run_id))
    if node is None or node.run_id != run.id:
        raise SecretHandleError("producer node 不存在或不属于该 Run")

    moment = now or datetime.now(UTC)
    handle_id = str(uuid.uuid4())
    expires_at = moment + timedelta(seconds=ttl)
    row = SecretHandle(
        id=handle_id,
        project_id=int(project_id),
        run_id=run.id,
        producer_node_run_id=node.id,
        secret_ref=f"{VAULT_REF_PREFIX}{handle_id}",
        key_name=str(key_name).strip(),
        secret_type=str(secret_type or secret_type_for_key(key_name, value))[:32],
        key_version=1,
        rotation_version=max(1, int(rotation_version)),
        allowed_consumer_nodes=[str(name) for name in allowed_consumer_nodes if str(name)],
        consumer_scope_json=dict(consumer_scope) if consumer_scope else None,
        expires_at=expires_at,
        metadata_json=metadata or None,
    )
    db.add(row)
    db.flush()
    (vault or VAULT).put(
        handle_id=handle_id,
        value=value,
        expires_at=expires_at,
        run_id=run.id,
        project_id=int(project_id),
    )
    return row


def resolve_secret_handle(
    db: Session,
    handle_id: str,
    *,
    project_id: int,
    run_id: str,
    consumer_node_key: str,
    vault: SecretVault | None = None,
    now: datetime | None = None,
) -> str:
    """受控解析：scope / TTL / 撤销 / 下游白名单全部满足才返回值。"""
    row = db.scalar(select(SecretHandle).where(SecretHandle.id == str(handle_id)))
    moment = now or datetime.now(UTC)
    if row is None:
        raise SecretAccessDenied("SECRET_HANDLE_NOT_FOUND", "Handle 不存在")

    def deny(code: str, message: str) -> None:
        row.access_audit_id = _audit_access(
            db,
            row=row,
            consumer_node_key=consumer_node_key,
            decision="DENY",
            reason_code=code,
            now=moment,
        )
        raise SecretAccessDenied(code, message)

    if int(row.project_id) != int(project_id) or row.run_id != str(run_id):
        deny("SECRET_HANDLE_SCOPE_DENIED", "Handle 不属于当前 Project/Run")
    if row.revoked_at is not None:
        deny("SECRET_HANDLE_REVOKED", "Handle 已撤销")
    if _aware(row.expires_at) <= moment:
        deny("SECRET_HANDLE_EXPIRED", "Handle 已过期")
    allowed = [str(name) for name in (row.allowed_consumer_nodes or [])]
    if allowed and consumer_node_key not in allowed:
        deny("SECRET_HANDLE_CONSUMER_DENIED", "当前节点不在允许消费列表中")
    entry = (vault or VAULT).get(row.id)
    if entry is None or entry.expires_at <= moment:
        # Vault 无明文（进程重启/已清理）→ fail closed，不回退到任何持久化值。
        deny("SECRET_VALUE_UNAVAILABLE", "Vault 无可用明文（可能已过期）")
    assert entry is not None
    row.access_audit_id = _audit_access(
        db,
        row=row,
        consumer_node_key=consumer_node_key,
        decision="ALLOW",
        reason_code="OK",
        now=moment,
    )
    row.access_count = int(row.access_count or 0) + 1
    row.last_accessed_at = moment
    db.flush()
    return entry.value


def revoke_secret_handle(
    db: Session, handle_id: str, *, vault: SecretVault | None = None, now: datetime | None = None
) -> SecretHandle:
    row = db.scalar(select(SecretHandle).where(SecretHandle.id == str(handle_id)))
    if row is None:
        raise SecretAccessDenied("SECRET_HANDLE_NOT_FOUND", "Handle 不存在")
    row.revoked_at = now or datetime.now(UTC)
    (vault or VAULT).drop(row.id)
    db.flush()
    return row


def revoke_run_handles(
    db: Session, run_id: str, *, vault: SecretVault | None = None, now: datetime | None = None
) -> int:
    """Run 终态/取消时清理临时 secret（V16-003 §11）。"""
    moment = now or datetime.now(UTC)
    rows = list(
        db.scalars(
            select(SecretHandle).where(
                SecretHandle.run_id == str(run_id),
                SecretHandle.revoked_at.is_(None),
            )
        )
    )
    store = vault or VAULT
    for row in rows:
        row.revoked_at = moment
        store.drop(row.id)
    db.flush()
    return len(rows)


def purge_expired_handles(
    db: Session, *, vault: SecretVault | None = None, now: datetime | None = None
) -> int:
    """过期清理：DB 标记 revoked + Vault 逐出（可被 Reconciler/定时任务调用）。"""
    moment = now or datetime.now(UTC)
    rows = list(
        db.scalars(
            select(SecretHandle).where(
                SecretHandle.revoked_at.is_(None),
                SecretHandle.expires_at <= moment,
            )
        )
    )
    store = vault or VAULT
    for row in rows:
        row.revoked_at = moment
        store.drop(row.id)
    db.flush()
    return len(rows)


def rotate_secret_handle(
    db: Session,
    handle_id: str,
    *,
    new_value: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    vault: SecretVault | None = None,
    now: datetime | None = None,
) -> SecretHandle:
    """轮换：创建新版本 Handle 并撤销旧 Handle（旧明文立即从 Vault 逐出）。"""
    old = db.scalar(select(SecretHandle).where(SecretHandle.id == str(handle_id)))
    if old is None:
        raise SecretAccessDenied("SECRET_HANDLE_NOT_FOUND", "Handle 不存在")
    if old.revoked_at is not None:
        raise SecretAccessDenied("SECRET_HANDLE_REVOKED", "Handle 已撤销，不能轮换")
    moment = now or datetime.now(UTC)
    store = vault or VAULT
    new_handle = create_secret_handle(
        db,
        project_id=int(old.project_id),
        run_id=str(old.run_id),
        producer_node_run_id=str(old.producer_node_run_id),
        key_name=str(old.key_name),
        value=new_value,
        allowed_consumer_nodes=list(old.allowed_consumer_nodes or []),
        ttl_seconds=ttl_seconds,
        secret_type=str(old.secret_type or "generic"),
        consumer_scope=dict(old.consumer_scope_json or {}) or None,
        rotation_version=int(old.rotation_version or 1) + 1,
        vault=store,
        now=moment,
    )
    new_handle.metadata_json = {
        **(new_handle.metadata_json or {}),
        "rotation_of": old.id,
    }
    old.revoked_at = moment
    store.drop(old.id)
    db.flush()
    return new_handle


def redacted_reference(row: SecretHandle) -> dict[str, Any]:
    """可放入普通 JSON 的 Handle 元信息（不含明文）。"""
    return {
        "secret_handle_id": row.id,
        "key_name": row.key_name,
        "secret_type": row.secret_type,
        "key_version": int(row.key_version or 1),
        "secret_ref": row.secret_ref,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "allowed_consumer_nodes": list(row.allowed_consumer_nodes or []),
    }


__all__ = [
    "DEFAULT_TTL_SECONDS",
    "MAX_TTL_SECONDS",
    "VAULT",
    "SecretAccessDenied",
    "SecretHandleError",
    "SecretVault",
    "SecretVaultBackend",
    "SecretVaultUnavailable",
    "create_secret_handle",
    "get_secret_vault",
    "purge_expired_handles",
    "redacted_reference",
    "resolve_secret_handle",
    "revoke_run_handles",
    "revoke_secret_handle",
    "secret_type_for_key",
]
