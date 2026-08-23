"""Durable, local-only release-control state and audit store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from cameltv_release.contracts import ReleaseManifest


@dataclass(frozen=True)
class Deployment:
    """Non-secret deployment read model."""

    id: str
    release_id: str
    manifest_sha256: str
    environment: str
    state: str


@dataclass(frozen=True)
class CreateDeploymentResult:
    """Outcome of a create-or-replay deployment command."""

    code: str
    deployment: Deployment | None = None
    replayed: bool = False


class ReleaseStore:
    """SQLite state store; it deliberately has no runner or network dependency."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS releases (
                    release_id TEXT PRIMARY KEY,
                    manifest_sha256 TEXT NOT NULL UNIQUE,
                    manifest_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deployments (
                    id TEXT PRIMARY KEY,
                    release_id TEXT NOT NULL REFERENCES releases(release_id),
                    manifest_sha256 TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    state TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(environment, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS environment_locks (
                    environment TEXT PRIMARY KEY,
                    deployment_id TEXT NOT NULL REFERENCES deployments(id)
                );
                CREATE TABLE IF NOT EXISTS deployment_events (
                    deployment_id TEXT NOT NULL REFERENCES deployments(id),
                    sequence INTEGER NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    previous_event_hash TEXT,
                    event_hash TEXT NOT NULL,
                    PRIMARY KEY (deployment_id, sequence)
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _deployment_from_row(row: sqlite3.Row) -> Deployment:
        return Deployment(
            id=row["id"],
            release_id=row["release_id"],
            manifest_sha256=row["manifest_sha256"],
            environment=row["environment"],
            state=row["state"],
        )

    def create_deployment(
        self,
        manifest: ReleaseManifest,
        environment: str,
        actor: str,
        idempotency_key: str,
    ) -> CreateDeploymentResult:
        """Persist one deployment (test or production), replaying an identical request safely."""
        if environment not in {"test", "production"}:
            return CreateDeploymentResult(code="UNSUPPORTED_ENVIRONMENT")
        manifest_hash = manifest.manifest_sha256()
        manifest_json = manifest.canonical_json().decode("utf-8")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                "SELECT * FROM deployments WHERE environment = ? AND idempotency_key = ?",
                (environment, idempotency_key),
            ).fetchone()
            if replay is not None:
                return CreateDeploymentResult(
                    code="IDEMPOTENT_REPLAY",
                    deployment=self._deployment_from_row(replay),
                    replayed=True,
                )
            existing_release = connection.execute(
                "SELECT manifest_sha256 FROM releases WHERE release_id = ?", (manifest.release_id,)
            ).fetchone()
            if existing_release is not None and existing_release["manifest_sha256"] != manifest_hash:
                return CreateDeploymentResult(code="RELEASE_ID_CONFLICT")
            lock = connection.execute(
                "SELECT deployment_id FROM environment_locks WHERE environment = ?", (environment,)
            ).fetchone()
            if lock is not None:
                return CreateDeploymentResult(code="ENVIRONMENT_LOCKED")
            connection.execute(
                "INSERT OR IGNORE INTO releases(release_id, manifest_sha256, manifest_json, created_at) VALUES (?, ?, ?, ?)",
                (manifest.release_id, manifest_hash, manifest_json, self._now()),
            )
            deployment_id = str(uuid4())
            connection.execute(
                "INSERT INTO deployments(id, release_id, manifest_sha256, environment, state, actor, idempotency_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (deployment_id, manifest.release_id, manifest_hash, environment, "DRAFT", actor, idempotency_key, self._now()),
            )
            connection.execute(
                "INSERT INTO environment_locks(environment, deployment_id) VALUES (?, ?)", (environment, deployment_id)
            )
            self._append_event_in_transaction(
                connection,
                deployment_id,
                "",
                "DRAFT",
                "register",
                f"{environment} deployment registered",
                actor,
            )
            deployment = Deployment(deployment_id, manifest.release_id, manifest_hash, environment, "DRAFT")
            return CreateDeploymentResult(code="ACCEPTED", deployment=deployment)

    def count_deployments(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM deployments").fetchone()[0])

    def get_deployment(self, deployment_id: str) -> Deployment:
        """Return a deployment read model or raise KeyError when it does not exist."""
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM deployments WHERE id = ?", (deployment_id,)).fetchone()
        if row is None:
            raise KeyError(deployment_id)
        return self._deployment_from_row(row)

    def list_events(self, deployment_id: str) -> list[dict[str, object]]:
        """Return ordered, non-secret event facts suitable for a future timeline."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence, from_state, to_state, phase, reason, actor FROM deployment_events WHERE deployment_id = ? ORDER BY sequence",
                (deployment_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_deployment(self, deployment_id: str) -> str:
        """Export deployment facts without embedding a manifest or Secret references."""
        deployment = self.get_deployment(deployment_id)
        return json.dumps(
            {
                "deployment_id": deployment.id,
                "release_id": deployment.release_id,
                "manifest_sha256": deployment.manifest_sha256,
                "environment": deployment.environment,
                "state": deployment.state,
                "events": self.list_events(deployment_id),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def transition_deployment(
        self,
        deployment_id: str,
        from_state: str,
        to_state: str,
        phase: str,
        reason: str,
        actor: str,
    ) -> bool:
        """Atomically change the expected state and append its audit event."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM deployments WHERE id = ?", (deployment_id,)).fetchone()
            if row is None or row["state"] != from_state:
                return False
            connection.execute("UPDATE deployments SET state = ? WHERE id = ?", (to_state, deployment_id))
            self._append_event_in_transaction(connection, deployment_id, from_state, to_state, phase, reason, actor)
            if to_state in {
                "TEST_VERIFIED",
                "TEST_FAILED",
                "TEST_ROLLED_BACK",
                "PRODUCTION_VERIFIED",
                "PROD_FAILED",
                "PROD_ROLLED_BACK",
                "CANCELLED",
            }:
                connection.execute("DELETE FROM environment_locks WHERE deployment_id = ?", (deployment_id,))
            return True

    @staticmethod
    def _event_hash(payload: dict[str, object]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def append_event(self, deployment_id: str, from_state: str, to_state: str, phase: str, reason: str, actor: str = "system") -> None:
        """Append a hash-linked event; callers own legal-transition validation."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._append_event_in_transaction(connection, deployment_id, from_state, to_state, phase, reason, actor)

    def _append_event_in_transaction(
        self,
        connection: sqlite3.Connection,
        deployment_id: str,
        from_state: str,
        to_state: str,
        phase: str,
        reason: str,
        actor: str,
    ) -> None:
        previous = connection.execute(
            "SELECT sequence, event_hash FROM deployment_events WHERE deployment_id = ? ORDER BY sequence DESC LIMIT 1",
            (deployment_id,),
        ).fetchone()
        sequence = 1 if previous is None else int(previous["sequence"]) + 1
        previous_hash = None if previous is None else previous["event_hash"]
        created_at = self._now()
        payload: dict[str, object] = {
            "deployment_id": deployment_id,
            "sequence": sequence,
            "from_state": from_state,
            "to_state": to_state,
            "phase": phase,
            "reason": reason,
            "actor": actor,
            "created_at": created_at,
            "previous_event_hash": previous_hash,
        }
        connection.execute(
            "INSERT INTO deployment_events(deployment_id, sequence, from_state, to_state, phase, reason, actor, created_at, previous_event_hash, event_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*payload.values(), self._event_hash(payload)),
        )

    def verify_event_chain(self, deployment_id: str) -> bool:
        """Return whether all ordered events form an intact hash chain."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM deployment_events WHERE deployment_id = ? ORDER BY sequence", (deployment_id,)
            ).fetchall()
        previous_hash: str | None = None
        for expected_sequence, row in enumerate(rows, start=1):
            if row["sequence"] != expected_sequence or row["previous_event_hash"] != previous_hash:
                return False
            payload: dict[str, object] = {
                "deployment_id": row["deployment_id"],
                "sequence": row["sequence"],
                "from_state": row["from_state"],
                "to_state": row["to_state"],
                "phase": row["phase"],
                "reason": row["reason"],
                "actor": row["actor"],
                "created_at": row["created_at"],
                "previous_event_hash": row["previous_event_hash"],
            }
            calculated = self._event_hash(payload)
            if calculated != row["event_hash"]:
                return False
            previous_hash = row["event_hash"]
        return True
