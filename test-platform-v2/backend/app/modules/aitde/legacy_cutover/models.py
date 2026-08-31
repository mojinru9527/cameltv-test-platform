"""AITDE V4.0 Legacy Cutover data models (V40).

Data model for the Legacy Usage Inventory (V40-001) and the Legacy Mapping /
Cutover Batch tables (V40-002) per the V4.0 plan §3 (``legacy_object_mappings``,
``cutover_batches``) + §4 (v1 endpoint inventory). Created by the M40 alembic
migration. String-valued enums so they stay stable across SQLite/PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.legacy_cutover.enums import (
    CutoverBatchStatus,
    EndpointStage,
    LegacyObjectType,
    MigrationStatus,
    UsageConsumerType,
)


class LegacyUsageRecord(Base):
    """V40-001: one row records actual observed usage of a legacy v1 surface.

    Surfaces are the v1 endpoints, pages and background jobs that V4.0 must retire
    or migrate. ``path`` is the route/path pattern, ``object_type``/``object_id``
    link back to the legacy fact object being retired, and the deprecation
    ``stage`` follows the V40-008 policy (ACTIVE -> DEPRECATED -> READONLY ->
    DISABLED). ``replacement_v2`` records the canonical successor so a consumer
    can be redirected safely before any write is disabled.
    """

    __tablename__ = "legacy_usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    consumer_type: Mapped[str] = mapped_column(
        String(16), default=UsageConsumerType.UNKNOWN.value, index=True
    )
    surface_kind: Mapped[str] = mapped_column(String(16), default="ENDPOINT", index=True)
    path: Mapped[str] = mapped_column(String(255), default="", index=True)
    method: Mapped[str] = mapped_column(String(16), default="")
    object_type: Mapped[str] = mapped_column(
        String(32), default=LegacyObjectType.TEST_CASE.value, index=True
    )
    object_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    owner: Mapped[str] = mapped_column(String(64), default="")
    traffic_count: Mapped[int] = mapped_column(Integer, default=0)
    replacement_v2: Mapped[str] = mapped_column(String(255), default="")
    deprecation_stage: Mapped[str] = mapped_column(
        String(16), default=EndpointStage.ACTIVE.value, index=True
    )
    sunset_date: Mapped[str | None] = mapped_column(String(32), default=None)
    rollback_switch: Mapped[str] = mapped_column(String(64), default="")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class LegacyObjectMapping(Base):
    """V40-002: a verified bidirectionality-preserving mapping legacy -> canonical.

    ``UNIQUE(legacy_type, legacy_id)`` keeps the mapping idempotent: a legacy
    object maps to exactly one canonical object and may be migrated once.
    ``migration_status`` follows :class:`MigrationStatus` and ``verified_at`` is
    only set once a post-migration equivalence check passes.
    """

    __tablename__ = "legacy_object_mappings"
    __table_args__ = (
        UniqueConstraint(
            "legacy_type", "legacy_id", name="uq_legacy_object_mapping"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    legacy_type: Mapped[str] = mapped_column(
        String(32), default=LegacyObjectType.TEST_CASE.value, index=True
    )
    legacy_id: Mapped[int] = mapped_column(Integer, index=True)
    canonical_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    canonical_id: Mapped[int] = mapped_column(Integer, index=True)
    migration_status: Mapped[str] = mapped_column(
        String(16), default=MigrationStatus.PENDING.value, index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CutoverBatch(Base):
    """V40-002: a coherent, idempotently-runnable group of legacy object migrations.

    ``criteria_json`` holds the selector that defines the batch (e.g. a filter /
    object-type / project subset); ``verification_json`` holds the post-run
    verification result. Streaming counters (``*_count``) let the batch be paused
    and resumed without double-counting.
    """

    __tablename__ = "cutover_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    batch_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    object_type: Mapped[str] = mapped_column(
        String(32), default=LegacyObjectType.TEST_CASE.value, index=True
    )
    criteria_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(
        String(16), default=CutoverBatchStatus.PENDING.value, index=True
    )
    planned_count: Mapped[int] = mapped_column(Integer, default=0)
    migrated_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    verification_json: Mapped[str] = mapped_column(Text, default="{}")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
