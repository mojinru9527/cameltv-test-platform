"""AITDE V3.9-R2 (DATA-002) — ExistingExecutor: real SELECT, never a recipe.

Locates an already-present row through the DataSource driver as a real
parameterized SELECT and returns the physical rows. When nothing matches the
constraints it raises ``DatabaseQueryError("NOT_FOUND")`` — it never reports a
``found`` recipe as success. The found entity is recorded with
``created_by_fixture=False`` (the fixture only *references* pre-existing data).
"""
from __future__ import annotations

import re
from typing import Any

from app.modules.aitde.drivers.database.base import DatabaseDriver, DatabaseQueryError

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


class ExistingExecutor:
    """Execute an EXISTING ``FIND`` against a READONLY data source."""

    @staticmethod
    def execute_find(
        driver: DatabaseDriver,
        table: str,
        where: dict[str, Any],
        *,
        row_limit: int = 100,
    ) -> dict[str, Any]:
        """SELECT a matching row and verify it is physically present.

        Raises ``DatabaseQueryError`` on an unsafe / non-allowlisted table or
        column, or ``NOT_FOUND`` when no row matches the constraints.
        """
        if not table or not _IDENT_RE.match(str(table)):
            raise DatabaseQueryError("UNSAFE_TABLE", str(table))
        if not isinstance(where, dict) or not where:
            raise DatabaseQueryError("EMPTY_WHERE", "no constraints given")
        if not all(_IDENT_RE.match(str(k)) for k in where):
            raise DatabaseQueryError("UNSAFE_COLUMN")

        cols = list(where.keys())
        clause = " AND ".join(f"{c} = :{c}" for c in cols)
        sql = f"SELECT * FROM {table} WHERE {clause}"
        rows = driver.execute_select(sql, where, table=str(table), row_limit=row_limit)
        if not rows:
            raise DatabaseQueryError("NOT_FOUND", f"no row in {table} for the constraints")
        return {"found": True, "physical_rows": rows}
