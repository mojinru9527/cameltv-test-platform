"""AUD-002：DB Read-only Query Registry 解析与执行。

v1.5 §01 AUD-002 不变量：

1. Workflow 只引用 ``query_key + typed_params``；SQL / 连接 / 表范围 / 限额全部由服务端登记；
2. ``project_id`` 由执行器**服务端注入**，覆盖任何客户端值，禁止跨租户读取；
3. 只允许登记过的单条 SELECT / WITH…SELECT；写语句、DDL、多语句、系统目录、文件函数一律拒绝；
4. 行数 / 执行时间 / 超时受控，结果只保留必要列并脱敏；
5. 生产环境默认拒绝（``is_production=True`` 的环境需显式放开，当前一律 BLOCKED）。
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.aiqe.drivers.db_readonly_driver import (
    DbReadonlyDriver,
    QueryResult,
    UnsafeSqlError,
    assert_readonly,
)
from app.aiqe.models.query_registry import RegisteredQuery
from app.aiqe.redaction import redact_mapping

_PARAM_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")
_FORBIDDEN_FRAGMENTS = (
    " for update",
    " select into ",
    " into outfile",
    " into dumpfile",
    "pg_read_file",
    "pg_read_binary_file",
    "lo_import",
    "lo_export",
    "pg_catalog",
    "information_schema",
    "sqlite_master",
    "sqlite_schema",
    "load_extension",
)
MAX_ROWS_LIMIT = 10_000
MAX_EXECUTION_MS_LIMIT = 60_000


class RegisteredQueryError(ValueError):
    """登记模板非法。"""


class QueryNotRegistered(LookupError):
    def __init__(self, query_key: str, project_id: int) -> None:
        super().__init__(f"未登记的 query_key: {query_key!r} (project={project_id})")
        self.code = "QUERY_NOT_REGISTERED"
        self.query_key = query_key


class QueryDenied(PermissionError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class QueryExecutionResult:
    query_key: str
    query_version: int
    query_hash: str
    row_count: int
    columns: list[str]
    rows: list[dict[str, Any]]
    duration_ms: int
    params_redacted: dict[str, Any]
    rows_digest: str
    connection_ref: str = ""
    max_rows: int = 0
    truncated: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """可持久化的脱敏摘要（不保存全量敏感行）。"""
        return {
            "query_key": self.query_key,
            "query_version": self.query_version,
            "query_hash": self.query_hash,
            "row_count": self.row_count,
            "columns": list(self.columns),
            "rows_digest": self.rows_digest,
            "duration_ms": self.duration_ms,
            "params_redacted": self.params_redacted,
            "max_rows": self.max_rows,
            "truncated": self.truncated,
        }


def statement_hash(statement: str, version: int) -> str:
    payload = f"{version}:{statement}".encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _validate_statement(statement: str, allowed_params: list[str]) -> None:
    try:
        cleaned = assert_readonly(statement)
    except UnsafeSqlError as exc:
        raise RegisteredQueryError(str(exc)) from exc
    lowered = " " + " ".join(cleaned.lower().split()) + " "
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise RegisteredQueryError(f"禁止的 SQL 片段: {fragment.strip()}")
    params = {match.group(1) for match in _PARAM_RE.finditer(cleaned)}
    declared = {str(name) for name in allowed_params}
    undeclared = params - declared
    if undeclared:
        raise RegisteredQueryError(f"语句使用了未声明的参数: {sorted(undeclared)}")
    unused = declared - params
    if unused:
        raise RegisteredQueryError(f"allowed_params 中存在未使用的参数: {sorted(unused)}")
    if "project_id" not in params:
        raise RegisteredQueryError("语句必须包含 :project_id 作为项目边界参数")


def register_query(
    db: Session,
    *,
    project_id: int,
    query_key: str,
    statement: str,
    allowed_params: list[str] | tuple[str, ...],
    connection_ref: str = "",
    max_rows: int = 100,
    max_execution_ms: int = 2000,
    result_schema: Mapping[str, Any] | None = None,
    project_scope: str = "current_project",
    created_by: int | None = None,
    approved_by: int | None = None,
) -> RegisteredQuery:
    key = str(query_key or "").strip()
    if not key or len(key) > 80:
        raise RegisteredQueryError("query_key 不能为空且不超过 80 字符")
    if project_scope != "current_project":
        raise RegisteredQueryError("project_scope 目前只支持 current_project")
    params = [str(name).strip() for name in allowed_params]
    if not params:
        raise RegisteredQueryError("allowed_params 不能为空")
    if "project_id" not in params:
        raise RegisteredQueryError("allowed_params 必须包含 project_id")
    rows = int(max_rows)
    if not 1 <= rows <= MAX_ROWS_LIMIT:
        raise RegisteredQueryError(f"max_rows 必须在 1..{MAX_ROWS_LIMIT}")
    timeout = int(max_execution_ms)
    if not 100 <= timeout <= MAX_EXECUTION_MS_LIMIT:
        raise RegisteredQueryError(f"max_execution_ms 必须在 100..{MAX_EXECUTION_MS_LIMIT}")
    _validate_statement(str(statement or ""), params)

    existing = list(
        db.scalars(
            select(RegisteredQuery).where(
                RegisteredQuery.project_id == int(project_id),
                RegisteredQuery.query_key == key,
            )
        )
    )
    version = max((int(row.version or 0) for row in existing), default=0) + 1
    row = RegisteredQuery(
        project_id=int(project_id),
        query_key=key,
        version=version,
        project_scope=project_scope,
        connection_ref=str(connection_ref or ""),
        statement=str(statement).strip(),
        allowed_params=params,
        max_rows=rows,
        max_execution_ms=timeout,
        result_schema=dict(result_schema) if result_schema else None,
        active=True,
        created_by=created_by,
        approved_by=approved_by,
    )
    db.add(row)
    db.flush()
    return row


def resolve_query(
    db: Session, *, project_id: int, query_key: str, version: int | None = None
) -> RegisteredQuery:
    rows = list(
        db.scalars(
            select(RegisteredQuery).where(
                RegisteredQuery.project_id == int(project_id),
                RegisteredQuery.query_key == str(query_key),
                RegisteredQuery.active.is_(True),
            )
        )
    )
    if not rows:
        raise QueryNotRegistered(str(query_key), int(project_id))
    if version is not None:
        for row in rows:
            if int(row.version) == int(version):
                return row
        raise QueryNotRegistered(f"{query_key}@{version}", int(project_id))
    return max(rows, key=lambda row: int(row.version or 0))


class QueryRegistryResolver:
    def __init__(self, db: Session) -> None:
        self._db = db

    def resolve(
        self, *, project_id: int, query_key: str, version: int | None = None, environment_id: int | None = None
    ) -> RegisteredQuery:
        # environment_id 预留给后续按环境细化登记；当前登记为项目级。
        del environment_id
        return resolve_query(
            self._db, project_id=project_id, query_key=query_key, version=version
        )


def default_connection_resolver(connection_ref: str) -> Engine:
    """按服务端配置解析只读连接；未配置即拒绝（fail closed）。"""
    from app.core.config import settings

    raw = getattr(settings, "aiqe_db_readonly_urls", "") or ""
    try:
        mapping = json.loads(raw) if raw.strip() else {}
    except ValueError as exc:
        raise QueryDenied("CONNECTION_CONFIG_INVALID", "AIQE_DB_READONLY_URLS 不是合法 JSON") from exc
    url = (mapping or {}).get(str(connection_ref or ""))
    if not url:
        raise QueryDenied(
            "CONNECTION_NOT_CONFIGURED", f"连接引用未配置: {connection_ref!r}"
        )
    from sqlalchemy import create_engine

    return create_engine(url, pool_pre_ping=True)


class DbReadonlyExecutor:
    """登记查询的唯一执行入口。"""

    def __init__(
        self,
        *,
        connection_resolver: Callable[[str], Engine] | None = None,
        db_session: Session | None = None,
    ) -> None:
        self._connection_resolver = connection_resolver or default_connection_resolver
        self._db = db_session

    def execute(
        self,
        db: Session | None,
        *,
        project_id: int,
        query_key: str,
        params: Mapping[str, Any] | None = None,
        version: int | None = None,
        environment_id: int | None = None,
    ) -> QueryExecutionResult:
        session = db or self._db
        if session is None:
            raise QueryDenied("SESSION_REQUIRED", "缺少 DB 会话，无法解析登记查询")
        self._assert_environment_allowed(session, environment_id)
        registered = resolve_query(
            session, project_id=int(project_id), query_key=query_key, version=version
        )
        bound = self._bind_params(registered, params or {}, project_id=int(project_id))

        engine = self._connection_resolver(str(registered.connection_ref or ""))
        driver = DbReadonlyDriver(engine, max_rows=int(registered.max_rows))
        import time

        started = time.monotonic()
        try:
            result: QueryResult = driver.query(
                registered.statement,
                bound,
                max_rows=int(registered.max_rows),
                statement_timeout_ms=int(registered.max_execution_ms),
            )
        finally:
            try:
                engine.dispose()
            except Exception:  # pragma: no cover - 连接释放失败不影响结论
                pass
        duration_ms = int((time.monotonic() - started) * 1000)
        if duration_ms > int(registered.max_execution_ms):
            raise QueryDenied(
                "QUERY_TIMEOUT",
                f"查询耗时 {duration_ms}ms 超过上限 {registered.max_execution_ms}ms",
            )

        redacted_rows = [redact_mapping(row) for row in result.rows]
        digest_payload = json.dumps(redacted_rows, sort_keys=True, ensure_ascii=False, default=str)
        return QueryExecutionResult(
            query_key=registered.query_key,
            query_version=int(registered.version),
            query_hash=statement_hash(registered.statement, int(registered.version)),
            row_count=result.row_count,
            columns=list(result.columns),
            rows=redacted_rows,
            duration_ms=duration_ms,
            params_redacted=redact_mapping(dict(params or {})),
            rows_digest="sha256:" + hashlib.sha256(digest_payload.encode("utf-8")).hexdigest(),
            connection_ref=str(registered.connection_ref or ""),
            max_rows=int(registered.max_rows),
        )

    @staticmethod
    def _assert_environment_allowed(session: Session, environment_id: int | None) -> None:
        if environment_id is None:
            return
        from app.models.environment import Environment

        env = session.get(Environment, int(environment_id))
        if env is None:
            raise QueryDenied("ENVIRONMENT_NOT_FOUND", f"环境不存在: {environment_id}")
        if bool(getattr(env, "is_production", False)):
            raise QueryDenied(
                "PRODUCTION_DB_READ_FORBIDDEN", "生产环境默认禁止 AIQE 直接读取数据库"
            )

    @staticmethod
    def _bind_params(
        registered: RegisteredQuery, params: Mapping[str, Any], *, project_id: int
    ) -> dict[str, Any]:
        allowed = {str(name) for name in (registered.allowed_params or [])}
        unknown = {str(key) for key in params} - allowed
        if unknown:
            raise QueryDenied("INVALID_PARAM", f"未声明的参数: {sorted(unknown)}")
        bound = {str(key): value for key, value in params.items()}
        # 服务端注入：任何客户端传入的 project_id 都会被覆盖。
        bound["project_id"] = int(project_id)
        return bound


__all__ = [
    "DbReadonlyExecutor",
    "QueryDenied",
    "QueryExecutionResult",
    "QueryNotRegistered",
    "QueryRegistryResolver",
    "RegisteredQueryError",
    "default_connection_resolver",
    "register_query",
    "resolve_query",
    "statement_hash",
]
