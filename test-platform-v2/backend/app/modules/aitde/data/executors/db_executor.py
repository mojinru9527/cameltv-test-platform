"""AITDE V3.9-R2 (DATA-002) DB_FIXTURE executor.

Turns a validated DataPlanStep ``set`` into a *real* INSERT + SELECT VERIFY against
the DataSource — never a recipe. The create only reports success when the row is
verified present (plan §26); a verify mismatch raises so the caller can ROLLBACK
and mark the fixture FAILED instead of READY.
"""
from __future__ import annotations

import re
from typing import Any

from app.modules.aitde.drivers.database.base import DatabaseDriver, DatabaseQueryError

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


class DbFixtureExecutor:
    """Execute a DB_FIXTURE create (single entity) via the driver."""

    @staticmethod
    def execute_create(
        driver: DatabaseDriver,
        table: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        """INSERT a row and verify it is present; return the physical row.

        Raises ``DatabaseQueryError`` when the table is not allowlisted / SQL is
        unsafe, or when the row cannot be verified after the write.
        """
        if not table or not _IDENT_RE.match(str(table)):
            raise DatabaseQueryError("UNSAFE_TABLE", str(table))
        if not isinstance(values, dict) or not values:
            raise DatabaseQueryError("EMPTY_VALUES")
        if not all(_IDENT_RE.match(str(k)) for k in values):
            raise DatabaseQueryError("UNSAFE_COLUMN")

        cols = list(values.keys())
        col_list = ", ".join(cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        driver.execute_dml(insert_sql, values, table=str(table))

        verify_sql = (
            f"SELECT * FROM {table} WHERE "
            + " AND ".join(f"{c} = :{c}" for c in cols)
        )
        rows = driver.execute_select(verify_sql, values, table=str(table))
        if not rows:
            raise DatabaseQueryError("VERIFY_MISMATCH", "row not found after insert")
        return {"created": True, "physical_row": rows[0]}
