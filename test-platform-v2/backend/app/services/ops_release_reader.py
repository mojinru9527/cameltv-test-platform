"""Read-only adapter for the independent release-control SQLite fact store."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


class OpsReleaseStoreUnavailable(RuntimeError):
    """The API has no configured, readable release-control state store."""


class OpsDeploymentNotFound(KeyError):
    """The requested deployment does not exist in the release-control store."""


@dataclass(frozen=True)
class OpsDeployment:
    id: str
    release_id: str
    manifest_sha256: str
    environment: str
    state: str
    created_at: str


@dataclass(frozen=True)
class OpsDeploymentEvent:
    sequence: int
    from_state: str
    to_state: str
    phase: str
    reason: str
    actor: str
    created_at: str


class OpsReleaseReader:
    """Read persisted non-secret facts without importing or mutating the domain store."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        if not self.database_path:
            raise OpsReleaseStoreUnavailable("release-control state store is not configured")
        path = Path(self.database_path)
        if not path.is_file():
            raise OpsReleaseStoreUnavailable("release-control state store is unavailable")
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _deployment(row: sqlite3.Row) -> OpsDeployment:
        return OpsDeployment(
            id=row["id"],
            release_id=row["release_id"],
            manifest_sha256=row["manifest_sha256"],
            environment=row["environment"],
            state=row["state"],
            created_at=row["created_at"],
        )

    def list_deployments(self) -> list[OpsDeployment]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT id, release_id, manifest_sha256, environment, state, created_at "
                    "FROM deployments ORDER BY created_at DESC, id DESC"
                ).fetchall()
        except sqlite3.Error as exc:
            raise OpsReleaseStoreUnavailable("release-control state store is unreadable") from exc
        return [self._deployment(row) for row in rows]

    def get_deployment(self, deployment_id: str) -> OpsDeployment:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT id, release_id, manifest_sha256, environment, state, created_at "
                    "FROM deployments WHERE id = ?",
                    (deployment_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise OpsReleaseStoreUnavailable("release-control state store is unreadable") from exc
        if row is None:
            raise OpsDeploymentNotFound(deployment_id)
        return self._deployment(row)

    def list_events(self, deployment_id: str) -> list[OpsDeploymentEvent]:
        self.get_deployment(deployment_id)
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT sequence, from_state, to_state, phase, reason, actor, created_at "
                    "FROM deployment_events WHERE deployment_id = ? ORDER BY sequence ASC",
                    (deployment_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise OpsReleaseStoreUnavailable("release-control state store is unreadable") from exc
        return [
            OpsDeploymentEvent(
                sequence=int(row["sequence"]),
                from_state=row["from_state"],
                to_state=row["to_state"],
                phase=row["phase"],
                reason=row["reason"],
                actor=row["actor"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
