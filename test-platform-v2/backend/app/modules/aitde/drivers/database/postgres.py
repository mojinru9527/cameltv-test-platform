"""PostgreSQL driver (V32-004)."""

from __future__ import annotations

from app.modules.aitde.drivers.database.base import DatabaseDriver


class PostgreSQLDriver(DatabaseDriver):
    source_type = "POSTGRES"

    def build_url(self) -> str:
        host = str(self.config.get("host", "127.0.0.1"))
        port = int(self.config.get("port", 5432))
        database = str(self.config.get("database", ""))
        user = str(self.config.get("username", "postgres"))
        # Password is resolved from secret_ref; never embedded in the loggable URL.
        return f"postgresql+psycopg2://{user}@{host}:{port}/{database}"
