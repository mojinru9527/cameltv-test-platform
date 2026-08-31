"""AITDE V4.0 Legacy Cutover string enums (V40).

String-valued enums stay stable across SQLite/PostgreSQL and are persisted as
plain string columns. Only values are stored; the enum name is NOT.
"""

from __future__ import annotations

from enum import Enum


class LegacyObjectType(str, Enum):
    """A legacy (v1) fact table object type being cut over."""

    VERSION_MISSION = "VERSION_MISSION"
    TEST_CASE = "TEST_CASE"
    TEST_PLAN = "TEST_PLAN"
    DATASET = "DATASET"
    API_TEST = "API_TEST"
    UI_TEST = "UI_TEST"
    AGENT_WORKBENCH = "AGENT_WORKBENCH"


class MigrationStatus(str, Enum):
    """Migration lifecycle of a single legacy object."""

    PENDING = "PENDING"
    MAPPED = "MAPPED"
    MIGRATING = "MIGRATING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"
    READONLY = "READONLY"


class CutoverBatchStatus(str, Enum):
    """Lifecycle of a cutover batch (a coherent group of legacy objects)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


class EndpointStage(str, Enum):
    """v1 API endpoint deprecation stage (V40-008)."""

    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    READONLY = "READONLY"
    DISABLED = "DISABLED"


class UsageConsumerType(str, Enum):
    """Who calls a legacy endpoint/page/job."""

    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
    UNKNOWN = "UNKNOWN"
