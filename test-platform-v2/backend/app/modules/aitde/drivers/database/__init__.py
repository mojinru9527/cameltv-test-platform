"""AITDE V3.2 database driver package (V32-004 / PR32-03).

Typed, policy-constrained access to MYSQL / POSTGRES test databases. Drivers
only ever build from a ``secret_ref`` (the reference); they never log the secret
value. Ping failures are reported by category, never by raw message, so no
credential leaks into API/log/evidence.
"""
from __future__ import annotations

from typing import Any

from app.modules.aitde.common.enums import DataSourceType
from app.modules.aitde.drivers.database.base import (
    DatabaseDriver,
    DatabaseDriverUnavailable,
)
from app.modules.aitde.drivers.database.mysql import MySQLDriver
from app.modules.aitde.drivers.database.postgres import PostgreSQLDriver

_DB_DRIVERS = {
    DataSourceType.MYSQL.value: MySQLDriver,
    DataSourceType.POSTGRES.value: PostgreSQLDriver,
}


class StaticDriver(DatabaseDriver):
    """STATIC data sources need no network; ping is trivially ok."""

    source_type = "STATIC"

    def build_url(self) -> str:  # pragma: no cover - never called
        raise NotImplementedError

    def ping(self, timeout: float = 5.0) -> tuple[bool, str]:
        return True, "ok"


def get_driver(
    source_type: str, config: dict[str, Any] | None = None, secret_ref: str | None = None
) -> DatabaseDriver:
    config = config or {}
    if source_type == DataSourceType.STATIC.value:
        return StaticDriver(config, secret_ref)
    cls = _DB_DRIVERS.get(source_type)
    if cls is None:
        raise DatabaseDriverUnavailable(f"unsupported:{source_type}")
    return cls(config, secret_ref)
