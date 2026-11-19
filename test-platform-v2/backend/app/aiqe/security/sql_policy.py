"""V16-004：SQL AST allowlist（sqlglot，纵深防御）。

定位
----
数据库执行的**主控制**是只读账号 + schema/table 权限 + 服务端 Query Registry；
本模块是第三道防线：在登记与执行两个时点用真实 AST 校验语句结构，阻断：

- 非单条 SELECT/UNION（DDL/DML/多语句/事务/GRANT/COPY/SELECT INTO）；
- 系统目录 / 跨 schema 访问（pg_catalog/information_schema/pg_class/pg_user/...）；
- 危险函数（pg_read_file/lo_import/dblink/pg_sleep/xp_cmdshell/load_extension/...）；
- 未在 ``allowed_tables`` 中的表（含逗号连表、JOIN、子查询、CTE）；
- 缺少真实租户谓词 ``project_id = :project_id``（``:project_id IS NOT NULL`` 视为绕过）。

限制：解析器只理解 SQL 语法，不替代数据库权限；执行账号仍必须只读且限定 schema。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

SYSTEM_SCHEMAS = frozenset(
    {
        "pg_catalog",
        "information_schema",
        "pg_toast",
        "sqlite_master",
        "sqlite_schema",
        "sqlite_temp_master",
        "mysql",
        "performance_schema",
        "sys",
    }
)
SYSTEM_TABLES = frozenset(
    {
        "pg_class",
        "pg_user",
        "pg_shadow",
        "pg_authid",
        "pg_roles",
        "pg_stat_activity",
        "pg_settings",
        "pg_proc",
        "pg_namespace",
        "pg_database",
        "sqlite_master",
        "sqlite_schema",
        "sqlite_temp_master",
        "dual",
    }
)
DANGEROUS_FUNCTIONS = frozenset(
    {
        "pg_read_file",
        "pg_read_binary_file",
        "pg_ls_dir",
        "lo_import",
        "lo_export",
        "dblink",
        "dblink_exec",
        "pg_sleep",
        "pg_sleep_for",
        "pg_terminate_backend",
        "pg_cancel_backend",
        "xp_cmdshell",
        "load_extension",
        "readfile",
        "writefile",
        "sys_exec",
        "sys_eval",
    }
)
FORBIDDEN_NODES: tuple[type, ...] = tuple(
    node
    for node in (
        getattr(exp, "Insert", None),
        getattr(exp, "Update", None),
        getattr(exp, "Delete", None),
        getattr(exp, "Create", None),
        getattr(exp, "Drop", None),
        getattr(exp, "Alter", None),
        getattr(exp, "Merge", None),
        getattr(exp, "Command", None),
        getattr(exp, "Transaction", None),
        getattr(exp, "Commit", None),
        getattr(exp, "Rollback", None),
        getattr(exp, "Grant", None),
        getattr(exp, "TruncateTable", None),
        getattr(exp, "Copy", None),
        getattr(exp, "Into", None),
        getattr(exp, "Lock", None),
    )
    if node is not None
)


class SqlPolicyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SqlPolicyResult:
    tables: tuple[str, ...]
    statement_hash: str
    has_project_predicate: bool


def statement_digest(statement: str) -> str:
    normalized = " ".join(str(statement or "").split())
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_table(name: str) -> str:
    return str(name or "").strip().strip('"').strip("`").lower()


def _is_select_root(node: exp.Expression) -> bool:
    if isinstance(node, exp.Select):
        return True
    if isinstance(node, exp.Union):
        return _all_union_selects(node)
    if isinstance(node, exp.Subquery):
        return _is_select_root(node.this)
    return False


def _all_union_selects(node: exp.Union) -> bool:
    left = node.this
    right = node.expression
    for part in (left, right):
        if isinstance(part, exp.Union):
            if not _all_union_selects(part):
                return False
        elif not isinstance(part, exp.Select):
            return False
    return True


def _check_dangerous_functions(tree: exp.Expression) -> None:
    for func in tree.find_all(exp.Func):
        name = ""
        if isinstance(func, exp.Anonymous):
            name = str(func.name or "").lower()
        else:
            name = str(getattr(func, "sql_name", lambda: "")()).lower()
        if name in DANGEROUS_FUNCTIONS:
            raise SqlPolicyError("QUERY_FUNCTION_DENIED", f"禁止的 SQL 函数: {name}")


def _check_project_predicate(tree: exp.Expression) -> bool:
    found = False
    for node in tree.find_all(exp.EQ):
        left, right = node.this, node.expression
        pairs = ((left, right), (right, left))
        for column, placeholder in pairs:
            if not isinstance(placeholder, exp.Placeholder):
                continue
            if str(placeholder.name or "").lower() != "project_id":
                continue
            if isinstance(column, exp.Column) and str(column.name or "").lower() == "project_id":
                found = True
    # 显式阻断 ``:project_id IS NOT NULL`` 之类的伪谓词。
    for node in tree.find_all(exp.Is):
        target = node.this
        if isinstance(target, exp.Placeholder) and str(target.name or "").lower() == "project_id":
            raise SqlPolicyError(
                "QUERY_TENANT_PREDICATE_INVALID",
                "租户边界必须是 project_id = :project_id 谓词，不能只用 IS NOT NULL",
            )
    return found


def validate_select(
    statement: str,
    *,
    allowed_tables: tuple[str, ...] | list[str] = (),
    require_project_predicate: bool = True,
    dialect: str = "",
) -> SqlPolicyResult:
    raw = str(statement or "").strip()
    if not raw:
        raise SqlPolicyError("QUERY_EMPTY", "SQL 不能为空")
    try:
        parsed = sqlglot.parse(raw, read=dialect or None)
    except ParseError as exc:
        raise SqlPolicyError("QUERY_PARSE_FAILED", f"SQL 解析失败: {exc}") from exc
    statements = [item for item in parsed if item is not None]
    if len(statements) != 1:
        raise SqlPolicyError("QUERY_MULTI_STATEMENT", "只允许单条 SELECT 语句")
    tree = statements[0]
    if not _is_select_root(tree):
        raise SqlPolicyError("QUERY_NOT_SELECT", "只允许 SELECT / UNION SELECT")
    for node_type in FORBIDDEN_NODES:
        if tree.find(node_type):
            raise SqlPolicyError(
                "QUERY_WRITE_FORBIDDEN", f"禁止的语句类型: {node_type.__name__}"
            )
    if isinstance(tree, exp.Select) and tree.args.get("into"):
        raise SqlPolicyError("QUERY_WRITE_FORBIDDEN", "禁止 SELECT INTO")

    _check_dangerous_functions(tree)

    tables: list[str] = []
    for table in tree.find_all(exp.Table):
        name = _normalize_table(table.name)
        schema = _normalize_table(table.db)
        catalog = _normalize_table(table.catalog)
        if not name:
            raise SqlPolicyError("QUERY_TABLE_INVALID", "表名不能为空")
        if schema in SYSTEM_SCHEMAS or catalog in SYSTEM_SCHEMAS or name in SYSTEM_TABLES:
            raise SqlPolicyError(
                "QUERY_SYSTEM_TABLE_DENIED", f"禁止访问系统表: {schema}.{name}"
            )
        if not schema and name.startswith("pg_"):
            raise SqlPolicyError("QUERY_SYSTEM_TABLE_DENIED", f"禁止访问系统表: {name}")
        tables.append(name)

    allow = {_normalize_table(item) for item in allowed_tables or () if str(item).strip()}
    if allow:
        denied = sorted({name for name in tables if name not in allow})
        if denied:
            raise SqlPolicyError(
                "QUERY_TABLE_NOT_ALLOWED", f"表不在登记允许列表: {denied}"
            )

    has_predicate = _check_project_predicate(tree)
    if require_project_predicate and not has_predicate:
        raise SqlPolicyError(
            "QUERY_TENANT_PREDICATE_MISSING",
            "语句必须包含 project_id = :project_id 作为租户边界谓词",
        )
    return SqlPolicyResult(
        tables=tuple(sorted(set(tables))),
        statement_hash=statement_digest(raw),
        has_project_predicate=has_predicate,
    )


__all__ = [
    "DANGEROUS_FUNCTIONS",
    "FORBIDDEN_NODES",
    "SYSTEM_SCHEMAS",
    "SYSTEM_TABLES",
    "SqlPolicyError",
    "SqlPolicyResult",
    "statement_digest",
    "validate_select",
]
