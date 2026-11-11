"""M2 / TA-014：DB Read-only Assertion Driver（13 号 §19 TA-014）。

- 仅允许单条 SELECT / WITH…SELECT（含 EXPLAIN SELECT）；
- 拒绝 INSERT/UPDATE/DELETE/DDL/PRAGMA/SET/事务控制等任何写操作与多语句；
- 行数超过 `max_rows` 抛 `RowLimitExceeded`（不静默截断）；
- SQLite 以 `PRAGMA query_only=ON`、PostgreSQL 以 `SET TRANSACTION READ ONLY` 双保险。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
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
)
_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_STRING = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"")
_TOKEN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN) + r")\b")


class UnsafeSqlError(ValueError):
    """非只读或多语句 SQL。"""


class RowLimitExceeded(RuntimeError):
    """查询结果超过行数上限。"""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int


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
    if tokens[0] == "WITH" and "SELECT" not in tokens:
        raise UnsafeSqlError("WITH 必须最终 SELECT")
    return sql.strip()


class DbReadonlyDriver:
    def __init__(self, engine: Engine, *, max_rows: int = 1000) -> None:
        self.engine = engine
        self.max_rows = max(1, int(max_rows))

    def query(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        *,
        max_rows: int | None = None,
    ) -> QueryResult:
        statement = assert_readonly(sql)
        limit = max(1, int(max_rows or self.max_rows))
        with self.engine.connect() as connection:
            dialect = connection.dialect.name
            if dialect == "sqlite":
                connection.exec_driver_sql("PRAGMA query_only=ON")
            elif dialect == "postgresql":
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            result = connection.execute(text(statement), params or {})
            columns = list(result.keys())
            rows = [dict(row) for row in result.mappings().fetchmany(limit + 1)]
        if len(rows) > limit:
            raise RowLimitExceeded(f"查询结果超过 {limit} 行（未截断）")
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
