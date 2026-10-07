"""Legacy Cutover string enums（平台简化批次收敛，仅保留执行运行时所需两类）。"""

from __future__ import annotations

from enum import StrEnum


class LegacyObjectType(StrEnum):
    """A legacy (v1) fact table object type being cut over."""

    VERSION_MISSION = "VERSION_MISSION"
    TEST_CASE = "TEST_CASE"
    TEST_PLAN = "TEST_PLAN"
    DATASET = "DATASET"
    API_TEST = "API_TEST"
    UI_TEST = "UI_TEST"
    AGENT_WORKBENCH = "AGENT_WORKBENCH"


class MigrationStatus(StrEnum):
    """Migration lifecycle of a single legacy object."""

    PENDING = "PENDING"
    MAPPED = "MAPPED"
    MIGRATING = "MIGRATING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"
    READONLY = "READONLY"
