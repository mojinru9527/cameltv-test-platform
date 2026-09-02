"""AITDE V3.9-R4 (REG-001) — ChangeProvider Registry + real source diff.

The Smart Regression ChangeSet detector historically trusted caller-supplied
``baseline``/``current`` payloads. REG-001 decouples "which diff" from "where the
snapshots come from": each ``ChangeProvider`` owns a ``load`` (it fetches its own
baseline/current snapshot from a ``source_ref``) and a ``diff``. The registry is
the single dispatch point; the automatic path always loads via the provider and
never trusts a caller payload (debug input stays ``source_type=MANUAL``).
"""
from __future__ import annotations

import json
from typing import Any, Callable, Protocol

from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import ChangeSetType
from app.modules.aitde.smart_regression import diff as diff_mod

# A provider that loads a snapshot and diffs two of them.
SnapshotLoader = Callable[[Session, int, str | None, str], dict[str, Any]]


class ChangeProvider(Protocol):
    change_type: str

    def load(self, db: Session, mission_id: int, source_ref: str | None) -> dict[str, Any]: ...

    def diff(self, baseline: dict, current: dict) -> list[dict[str, Any]]: ...


def _default_loader(
    db: Session, mission_id: int, source_ref: str | None, change_type: str
) -> dict[str, Any]:
    """Store-backed snapshot loader (Batch 208, C4).

    Supported refs:
    - ``inline:<json>`` — debug/tester-supplied snapshot;
    - ``env_snapshot:<id>`` — EnvironmentSnapshot.service_versions mapped to
      the ENVIRONMENT diff shape ({service: {value, sensitivity}});
    - ``data_source:<id>:<kind>`` — DataSource.config_json as the snapshot
      payload (kind in OPENAPI/DB_SCHEMA/PRD/UI_DISCOVERY).
    Anything else raises — an unresolvable ref must never silently produce an
    empty snapshot that vacuously diffs to "no change".
    """
    if source_ref and source_ref.startswith("inline:"):
        try:
            loaded = json.loads(source_ref[len("inline:"):])
        except (ValueError, TypeError):
            return {}
        return loaded if isinstance(loaded, dict) else {}
    if source_ref and source_ref.startswith("env_snapshot:"):
        from app.modules.aitde.execution.models import EnvironmentSnapshot

        try:
            snapshot_id = int(source_ref[len("env_snapshot:"):])
        except ValueError as exc:
            raise ValueError(f"invalid env_snapshot ref: {source_ref!r}") from exc
        row = db.get(EnvironmentSnapshot, snapshot_id)
        if row is None:
            raise ValueError(f"env_snapshot not found: {snapshot_id}")
        versions = json.loads(row.service_versions_json or "{}")
        if not isinstance(versions, dict):
            return {}
        return {
            str(k): {"value": str(v), "sensitivity": "public"}
            for k, v in versions.items()
        }
    if source_ref and source_ref.startswith("data_source:"):
        parts = source_ref.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"invalid data_source ref (expected data_source:<id>:<kind>): {source_ref!r}"
            )
        from app.modules.aitde.data.models import DataSource

        kind = parts[2].upper()
        if kind not in {"OPENAPI", "DB_SCHEMA", "PRD", "UI_DISCOVERY"}:
            raise ValueError(f"unsupported data_source kind: {kind}")
        try:
            data_id = int(parts[1])
        except ValueError as exc:
            raise ValueError(f"invalid data_source id: {parts[1]!r}") from exc
        row = db.get(DataSource, data_id)
        if row is None:
            raise ValueError(f"data_source not found: {data_id}")
        cfg = json.loads(row.config_json or "{}")
        return cfg if isinstance(cfg, dict) else {"_raw": cfg}
    raise ValueError(
        f"unresolved source_ref for {change_type}: {source_ref!r} — "
        "supported: inline:<json> | env_snapshot:<id> | data_source:<id>:<kind>"
    )


class SnapshotDiffProvider:
    """A ChangeProvider wiring a diff function to a snapshot loader."""

    def __init__(
        self,
        change_type: str,
        diff_fn: Callable[[dict, dict], list[dict[str, Any]]],
        loader: SnapshotLoader | None = None,
    ):
        self.change_type = change_type.upper()
        self._diff = diff_fn
        self._loader = loader or _default_loader

    def load(self, db: Session, mission_id: int, source_ref: str | None) -> dict[str, Any]:
        return self._loader(db, mission_id, source_ref, self.change_type)

    def diff(self, baseline: dict, current: dict) -> list[dict[str, Any]]:
        return self._diff(baseline or {}, current or {})


class ChangeProviderRegistry:
    """Dispatch by ``change_type``; PROVIDER mode loads via the provider, never
    via a caller-supplied payload."""

    def __init__(self) -> None:
        self._providers: dict[str, ChangeProvider] = {}

    def register(self, provider: ChangeProvider) -> None:
        self._providers[provider.change_type.upper()] = provider

    def get(self, change_type: str | None) -> ChangeProvider | None:
        return self._providers.get((change_type or "").upper())

    def load_and_diff(
        self,
        change_type: str | None,
        db: Session,
        mission_id: int,
        source_from_ref: str | None,
        source_to_ref: str | None,
    ) -> list[dict[str, Any]]:
        """Load baseline + current snapshots via the provider and diff them."""
        provider = self.get(change_type)
        if provider is None:
            raise ValueError(f"unknown change_type: {change_type}")
        baseline = provider.load(db, mission_id, source_from_ref)
        current = provider.load(db, mission_id, source_to_ref)
        return provider.diff(baseline, current)


# The canonical registry — real providers load their own OpenAPI / DB-schema /
# requirement / environment snapshots from a source_ref (REG-001).
change_provider_registry = ChangeProviderRegistry()
change_provider_registry.register(
    SnapshotDiffProvider(ChangeSetType.OPENAPI.value, diff_mod.diff_openapi)
)
change_provider_registry.register(
    SnapshotDiffProvider(ChangeSetType.DB_SCHEMA.value, diff_mod.diff_db_schema)
)
change_provider_registry.register(
    SnapshotDiffProvider(ChangeSetType.PRD.value, diff_mod.diff_requirement)
)
change_provider_registry.register(
    SnapshotDiffProvider(ChangeSetType.ENVIRONMENT.value, diff_mod.diff_environment)
)
change_provider_registry.register(
    SnapshotDiffProvider(ChangeSetType.UI_DISCOVERY.value, diff_mod.diff_ui_discovery)
)
