"""MySQL driver (V32-004)."""

from __future__ import annotations

from app.modules.aitde.drivers.database.base import DatabaseDriver


class MySQLDriver(DatabaseDriver):
    source_type = "MYSQL"

    def build_url(self) -> str:
        host = str(self.config.get("host", "127.0.0.1"))
        port = int(self.config.get("port", 3306))
        database = str(self.config.get("database", ""))
        user = str(self.config.get("username", "root"))
        # Password is resolved from secret_ref; never embedded in the loggable URL.
        return f"mysql+pymysql://{user}@{host}:{port}/{database}"
