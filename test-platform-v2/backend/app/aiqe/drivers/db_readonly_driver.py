"""M2 / TA-014 + v1.4 FIX-007：DB Read-only Driver。

安全边界：
- 只允许单条 SELECT / WITH…SELECT / EXPLAIN SELECT；
- 拒绝写入、DDL、事务控制、存储过程、文件读写、`pg_sleep` / `sleep`；
- 优先只允许登记过的 query key（模板），模型不能传任意 SQL；
- 表/Schema 通过 Project Adapter allowlist；
- SQLite `PRAGMA query_only=ON`；PostgreSQL `SET TRANSACTION READ ONLY` + statement_timeout；
- 最大返回行数（超限报错，不静默截断）、最大字段长度（超长截断并标记）；
- 所有拒绝产生可审计事件（audit_hook / `last_audit`）。
"""
from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Engine, text

_FORBIDDEN = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "CALL",
    "COPY",
    "VACUUM",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "SET",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "RELEASE",
    "LOCK",
    "INTO",
)
_FORBIDDEN_FUNCTIONS = (
    "PG_SLEEP",
    "SLEEP",
    "BENCHMARK",
    "LOAD_FILE",
    "LO_IMPORT",
    "DBLINK",
    "XP_CMDSHELL",
    "PG_READ_FILE",
    "PG_READ_BINARY_FILE",
)
_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_STRING = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"")
_TOKEN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN) + r")\b")
_FUNCTION_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN_FUNCTIONS) + r")\s*\(", re.IGNORECASE)
_TABLE_RE = re.compile(
    r"\b(?:FROM|JOIN|UPDATE|INTO)\s+([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)",
    re.IGNORECASE,
)


class UnsafeSqlError(ValueError):
    """非只读、多语句、越权表或危险函数。"""


class RowLimitExceeded(RuntimeError):
    """查询结果超过行数上限。"""


class QueryNotRegistered(ValueError):
    """query_key 未登记。"""


@dataclass
class QueryTemplate:
    key: str
    sql: str
    allowed_tables: tuple[str, ...] = ()
    max_rows: int = 1000
    max_field_chars: int = 2000
    description: str = ""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    query_key: str = ""
    elapsed_ms: int = 0
    truncated_fields: list[str] = field(default_factory=list)


@dataclass
class AuditEvent:
    action: str
    query_key: str
    allowed: bool
    reason: str = ""
    sql_preview: str = ""


class QueryRegistry:
    """登记过的只读查询模板；来源可为 JSON（AIQE_DB_QUERY_REGISTRY_JSON）。"""

    def __init__(self, templates: Mapping[str, Any] | Iterable[QueryTemplate] | None = None) -> None:
        self._templates: dict[str, QueryTemplate] = {}
        if isinstance(templates, Mapping):
            for key, raw in templates.items():
                if isinstance(raw, QueryTemplate):
                    self._templates[str(key)] = raw
                elif isinstance(raw, Mapping):
                    self._templates[str(key)] = QueryTemplate(
                        key=str(key),
                        sql=str(raw.get("sql") or ""),
                        allowed_tables=tuple(str(item) for item in raw.get("allowed_tables") or ()),
                        max_rows=int(raw.get("max_rows") or 1000),
                        max_field_chars=int(raw.get("max_field_chars") or 2000),
                        description=str(raw.get("description") or ""),
                    )
        else:
            for template in templates or ():
                self._templates[template.key] = template

    @classmethod
    def from_json(cls, raw: str) -> QueryRegistry:
        if not raw or not raw.strip():
            return cls()
        parsed = json.loads(raw)
        if not isinstance(parsed, Mapping):
            raise ValueError("query registry 必须是对象")
        return cls(parsed)

    def get(self, key: str) -> QueryTemplate:
        if str(key) not in self._templates:
            raise QueryNotRegistered(f"query key 未登记: {key}")
        return self._templates[str(key)]

    def keys(self) -> list[str]:
        return sorted(self._templates)


def assert_readonly(sql: str) -> str:
    if not isinstance(sql, str) or not sql.strip():
        raise UnsafeSqlError("SQL 不能为空")
    cleaned = _COMMENT.sub(" ", sql)
    # 去掉字符串字面量，避免 'update' 之类误报
    cleaned = _STRING.sub("''", cleaned)
    statements = [part.strip() for part in cleaned.split(";") if part.strip()]
    if len(statements) != 1:
        raise UnsafeSqlError("只允许单条语句")
    statement = statements[0]
    tokens = [token.upper() for token in _TOKEN.findall(statement)]
    if not tokens:
        raise UnsafeSqlError("无法识别的 SQL")
    if tokens[0] not in ("SELECT", "WITH", "EXPLAIN"):
        raise UnsafeSqlError(f"只允许 SELECT/WITH/EXPLAIN，实际 {tokens[0]}")
    forbidden = _FORBIDDEN_RE.search(statement.upper())
    if forbidden:
        raise UnsafeSqlError(f"禁止的 SQL 关键字: {forbidden.group(1)}")
    dangerous = _FUNCTION_RE.search(statement)
    if dangerous:
        raise UnsafeSqlError(f"禁止的危险函数: {dangerous.group(1)}")
    if tokens[0] == "WITH" and "SELECT" not in tokens:
        raise UnsafeSqlError("WITH 必须最终 SELECT")
    if tokens[0] == "EXPLAIN" and "SELECT" not in tokens:
        raise UnsafeSqlError("EXPLAIN 只允许解释 SELECT")
    return sql.strip()


def _referenced_tables(sql: str) -> set[str]:
    cleaned = _STRING.sub("''", _COMMENT.sub(" ", sql))
    cte_aliases = {
        match.group(1).lower()
        for match in re.finditer(
            r"(?:\bWITH\b|,)\s*([A-Za-z_][\w$]*)\s+AS\s*\(", cleaned, re.IGNORECASE
        )
    }
    tables: set[str] = set()
    for match in _TABLE_RE.finditer(cleaned):
        name = match.group(1)
        if name.startswith("("):
            continue
        normalized = name.split(".")[-1].strip('"').lower()
        if normalized in cte_aliases:
            continue
        tables.add(normalized)
    return tables


def _rows_from_result(
    result: Any, limit: int, max_field_chars: int
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    truncated: list[str] = []
    for row in result.mappings().fetchmany(limit + 1):
        cleaned: dict[str, Any] = {}
        for key, value in dict(row).items():
            if isinstance(value, str) and len(value) > max_field_chars:
                cleaned[key] = value[:max_field_chars] + "…[truncated]"
                truncated.append(str(key))
            else:
                cleaned[key] = value
        rows.append(cleaned)
    return rows, truncated


class DbReadonlyDriver:
    def __init__(
        self,
        engine: Engine,
        *,
        max_rows: int = 1000,
        max_field_chars: int = 2000,
        allowed_tables: Iterable[str] | None = None,
        registry: QueryRegistry | None = None,
        statement_timeout_ms: int = 5000,
        audit_hook: Callable[[AuditEvent], None] | None = None,
    ) -> None:
        self.engine = engine
        self.max_rows = max(1, int(max_rows))
        self.max_field_chars = max(1, int(max_field_chars))
        self.allowed_tables = {str(item).lower() for item in (allowed_tables or ())}
        self.registry = registry or QueryRegistry()
        self.statement_timeout_ms = max(1, int(statement_timeout_ms))
        self.audit_hook = audit_hook
        self.last_audit: list[AuditEvent] = []

    def _audit(
        self, action: str, query_key: str, allowed: bool, reason: str = "", sql: str = ""
    ) -> None:
        event = AuditEvent(
            action=action,
            query_key=query_key,
            allowed=allowed,
            reason=reason,
            sql_preview=(sql or "")[:200],
        )
        self.last_audit.append(event)
        if self.audit_hook is not None:
            self.audit_hook(event)

    def _check_tables(self, sql: str, allowed_tables: Iterable[str] | None, query_key: str) -> None:
        allow = {str(item).lower() for item in (allowed_tables or self.allowed_tables)}
        if not allow:
            return
        referenced = _referenced_tables(sql)
        blocked = sorted(referenced - allow)
        if blocked:
            self._audit("query", query_key, False, f"越权表: {','.join(blocked)}", sql)
            raise UnsafeSqlError(f"查询了未允许的表: {', '.join(blocked)}")

    def query(
        self,
        sql: str | None = None,
        params: Mapping[str, Any] | None = None,
        *,
        max_rows: int | None = None,
        query_key: str = "",
        timeout_ms: int | None = None,
    ) -> QueryResult:
        template: QueryTemplate | None = None
        if query_key:
            try:
                template = self.registry.get(query_key)
            except QueryNotRegistered as exc:
                self._audit("query", query_key, False, str(exc), sql or "")
                raise
            statement = template.sql
            limit = max(1, int(max_rows or template.max_rows or self.max_rows))
            max_field_chars = int(template.max_field_chars or self.max_field_chars)
            allowed_tables = template.allowed_tables or self.allowed_tables
        else:
            if not sql:
                self._audit("query", "", False, "缺少 sql/query_key")
                raise UnsafeSqlError("未登记查询必须显式提供 SQL（仅测试/迁移允许）")
            statement = sql
            limit = max(1, int(max_rows or self.max_rows))
            max_field_chars = self.max_field_chars
            allowed_tables = self.allowed_tables

        statement = assert_readonly(statement)
        self._check_tables(statement, allowed_tables, query_key)
        timeout = max(1, int(timeout_ms or self.statement_timeout_ms))
        started = time.monotonic()
        try:
            with self.engine.connect() as connection:
                dialect = connection.dialect.name
                if dialect == "postgresql":
                    # 显式只读事务：statement_timeout 必须在该事务内 SET LOCAL。
                    with connection.begin():
                        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                        connection.exec_driver_sql(f"SET LOCAL statement_timeout = {timeout}")
                        result = connection.execute(text(statement), dict(params or {}))
                        columns = list(result.keys())
                        rows, truncated = _rows_from_result(
                            result, limit, max_field_chars
                        )
                else:
                    if dialect == "sqlite":
                        connection.exec_driver_sql("PRAGMA query_only=ON")
                    result = connection.execute(text(statement), dict(params or {}))
                    columns = list(result.keys())
                    rows, truncated = _rows_from_result(result, limit, max_field_chars)
        except UnsafeSqlError:
            raise
        except Exception as exc:
            self._audit("query", query_key, False, f"{type(exc).__name__}: {exc}", statement)
            raise
        if len(rows) > limit:
            self._audit("query", query_key, False, f"超过行数上限 {limit}", statement)
            raise RowLimitExceeded(f"查询结果超过 {limit} 行（未截断）")
        elapsed_ms = int((time.monotonic() - started) * 1000)
        self._audit("query", query_key, True, "", statement)
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            query_key=query_key,
            elapsed_ms=elapsed_ms,
            truncated_fields=sorted(set(truncated)),
        )
